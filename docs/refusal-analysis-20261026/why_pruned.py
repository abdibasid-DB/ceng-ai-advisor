"""For the topic-check and claim-support wrong refusals: which guard in cited_claim_supported drops each sentence."""
import collections
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from backend.app.rag import rag_pipeline as rp  # noqa: E402
from backend.app.rag.retriever import Retriever  # noqa: E402
from backend.app.core.retrieval_config import SENTENCE_PASSAGE_SIMILARITY_THRESHOLD as SEM  # noqa: E402

rp.configure_semantic_encoder(Retriever().encode_texts)
SPLIT = r"(?<=[.!?\]])\s+(?=[A-Z\-*•\d(]|\[(?!S\d+\]))"


def why(sentence, item):
    """Name of the first guard that rejects the sentence for this passage, or 'ok'."""
    passage = str(item.get("passage") or "")
    claim = rp.strip_citation_text(sentence)
    if not rp.ABSENCE_CLAIM.search(sentence) and rp.polarity_conflicts_with_passage(claim, passage):
        return "polarity"
    if rp.SPECULATIVE_CLAIM.search(claim) and not rp.SPECULATIVE_CLAIM.search(passage):
        return "speculative"
    source_name = " ".join(str(item.get(k) or "") for k in ("title", "source_name"))
    numbers = set(re.findall(rp.NUMBER, claim)) - set(re.findall(rp.NUMBER, source_name))
    if not all(rp.number_used_as_in_passage(n, claim, passage) for n in numbers):
        return "number"
    if rp.COMPARATIVE_CLAIM.search(claim) and not re.search(r"\b(?:than|compared|whereas|unlike)\b", passage, re.I):
        return "comparative"
    if not rp.cited_claim_supported(sentence, item):
        lexical = rp.claim_support_score(claim, item)
        semantic = rp.semantic_sentence_support(claim, item)
        if lexical < 0.25 and (semantic is None or semantic < SEM):
            return f"overlap(lex={lexical:.2f},sem={semantic if semantic is None else round(semantic, 2)})"
        return "strong/relation/causal"
    return "ok"


rows = json.loads((ROOT / "docs/final-evaluation-20261025/full200-results.json").read_text(encoding="utf-8"))["results"]
guards = collections.Counter()
semantic_scores = []
for r in rows:
    rm = r["diagnostics"].get("retrieval_metadata") or {}
    reason = rm.get("unsupported_reason") or ""
    if r["evaluation_label"] != "incorrect_refusal_evidence_exists" or not ("did not address" in reason or "could not be matched" in reason or "does not support" in reason):
        continue
    context = {item.get("label"): item for item in r["retrieved_context"]}
    raw = rp.normalize_answer(rm.get("discarded_generation") or "")
    raw = re.split(r"\n\s*USED_SOURCES", raw)[0]
    print(f"\n== {r['id']} {r['question']}  [{reason[:30]}]")
    for line in raw.splitlines():
        for sentence in re.split(SPLIT, line.strip()):
            if not sentence.strip():
                continue
            labels = [label for label in rp.extract_citation_labels(sentence) if label in context]
            if not labels:
                guards["no valid label"] += 1
                print(f"   [no label] {sentence[:110]}")
                continue
            results = {label: why(sentence, context[label]) for label in labels}
            best = "ok" if "ok" in results.values() else next(iter(results.values()))
            key = best.split("(")[0]
            guards[key] += 1
            if key == "overlap":
                semantic_scores.append(max(rp.semantic_sentence_support(sentence, context[label]) or 0 for label in labels))
            print(f"   [{best}] {sentence[:110]}")
print("\nguards:", dict(guards))
print("best semantic score of overlap-rejected sentences:", sorted(round(s, 2) for s in semantic_scores))
