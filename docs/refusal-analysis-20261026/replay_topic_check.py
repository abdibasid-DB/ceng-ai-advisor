"""Replay the post-generation topic-term check on frozen full-200 results, without the LLM.

For the 25 wrong refusals of the topic check: re-run citation validation on the
stored model output and stored context, then report the focus terms, which were
covered before and after pruning, and the question-answer similarity. For the
answered cases (supported and unsupported) report the same numbers for the
final answer, to see whether a looser check would also let more bad answers through.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from backend.app.rag import rag_pipeline as rp  # noqa: E402
from backend.app.rag.retriever import Retriever  # noqa: E402

retriever = Retriever()
rp.configure_semantic_encoder(retriever.encode_texts)

EXCLUDED = {
    "computer engineering", "ceng", "ce", "computer", "engineering", "career", "careers",
    "job", "jobs", "work", "study", "studying", "taking", "after", "still",
    "graduate", "graduates", "future", "technologies", "technology", "follow",
    "good", "choice", "choose", "like", "hate", "first", "right", "project",
    "will", "would", "can", "could", "should", "shall", "may", "might", "must",
    "not", "very", "really", "much",
}


def coverage(question, answer):
    focus = rp.content_terms(question) - EXCLUDED - rp.EMOTIONAL_TERMS
    normalized = rp.normalize_answer(answer).lower()
    words = set(re.findall(r"[a-z0-9+#]+", normalized))
    stems = {rp.word_stem(w) for w in words}
    covered = {t for t in focus if rp.term_supported_by_evidence(t, normalized) or (" " not in t and rp.word_stem(t) in stems)
               or (len(t) >= 5 and any(w.startswith(t) for w in words))}
    need = 2 if len(focus) >= 3 else 1
    sim = rp.semantic_similarity(rp.strip_retrieval_annotations(question), " ".join(rp.strip_citation_text(answer).split()))
    return sorted(focus), sorted(covered), need, None if sim is None else round(sim, 3)


rows = json.loads((ROOT / "docs/final-evaluation-20261025/full200-results.json").read_text(encoding="utf-8"))["results"]
out = {"refused": [], "answered": []}
for r in rows:
    dg = r["diagnostics"]
    rm = dg.get("retrieval_metadata") or {}
    question = rp.strip_retrieval_annotations(dg.get("resolved_question") or r["question"])
    if r["evaluation_label"] == "incorrect_refusal_evidence_exists" and "did not address" in (rm.get("unsupported_reason") or ""):
        raw = rp.normalize_answer(rm.get("discarded_generation") or "")
        validation = rp.validate_citations(raw, r["retrieved_context"])
        final = validation.answer if validation.valid else ""
        reproduced = rp.unsupported_generated_answer_reason(question, final, r["retrieved_context"]) if final else "citation invalid"
        f_focus, f_cov, need, f_sim = coverage(question, final) if final else ([], [], 0, None)
        _, raw_cov, _, raw_sim = coverage(question, raw)
        out["refused"].append({"id": r["id"], "question": question, "focus": f_focus, "need": need,
                               "covered_after_pruning": f_cov, "covered_raw": raw_cov, "sim_after": f_sim, "sim_raw": raw_sim,
                               "reproduced": reproduced, "final": final, "repairs": validation.repair_actions if hasattr(validation, "repair_actions") else None})
    elif dg.get("status") == "answered" and r["evaluation_label"] in ("correct_evidence_supported", "unsupported_incorrect_or_misleading"):
        focus, cov, need, sim = coverage(question, r["answer"])
        out["answered"].append({"id": r["id"], "label": r["evaluation_label"], "focus": focus, "covered": cov, "need": need, "sim": sim})

Path(__file__).with_name("replay_topic_check.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
for row in out["refused"]:
    print(f"{row['id']:5} need {row['need']} covered {len(row['covered_after_pruning'])}/{len(row['focus'])} raw {len(row['covered_raw'])} "
          f"sim {row['sim_after']} raw {row['sim_raw']} | {row['reproduced'] and row['reproduced'][:40]} | focus {row['focus']}")
for label in ("correct_evidence_supported", "unsupported_incorrect_or_misleading"):
    group = [a for a in out["answered"] if a["label"] == label]
    sims = sorted(a["sim"] for a in group if a["sim"] is not None)
    passed_by_terms = sum(1 for a in group if len(a["covered"]) >= a["need"] or not a["focus"])
    print(label, len(group), "passed by terms", passed_by_terms, "sims", sims)
