"""Offline: would the 46 wrong refusals pass validation if the model's own end labels
were attached to uncited sentences under cited_claim_supported (the inline-citation
standard) instead of claim_supported_by_context (lexical overlap >= 0.5)?

Replays validate_citations + unsupported_generated_answer_reason on the stored model
output and stored context. Pre-generation refusals are not affected by this change.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from backend.app.rag import rag_pipeline as rp  # noqa: E402
from backend.app.rag.retriever import Retriever  # noqa: E402

rp.configure_semantic_encoder(Retriever().encode_texts)
original_repair = rp.repair_missing_inline_citations


def run(row, variant):
    rm = row["diagnostics"].get("retrieval_metadata") or {}
    question = rp.strip_retrieval_annotations(row["diagnostics"].get("resolved_question") or row["question"])
    raw = rp.normalize_answer(rm.get("discarded_generation") or "")
    if not raw:
        return "no generation (pre-generation gate)", None
    rp.claim_supported_by_context.__globals__["_VARIANT"] = variant
    validation = rp.validate_citations(raw, row["retrieved_context"])
    if not validation.valid:
        return f"citation invalid: {validation.reason}", None
    reason = rp.unsupported_generated_answer_reason(question, validation.answer, row["retrieved_context"])
    if reason:
        return reason, validation.answer
    if rp.is_insufficient_answer(validation.answer):
        return "insufficient", None
    return "ANSWERED", validation.answer


# Variant: inside repair_missing_inline_citations, fallback (model's own) labels use cited_claim_supported.
source = Path(rp.__file__).read_text(encoding="utf-8")
start = source.index("def repair_missing_inline_citations(")
end = source.index("\ndef strip_trailing_source_labels(")
patched = source[start:end].replace(
    """            supported_labels = tuple(
                label for label in fallback_labels
                if claim_supported_by_context(sentence, context_by_label[label])
            )""",
    """            supported_labels = tuple(
                label for label in fallback_labels
                if (cited_claim_supported if _VARIANT else claim_supported_by_context)(sentence, context_by_label[label])
            )""",
)
assert patched != source[start:end]
exec(compile(patched, "patched_repair", "exec"), rp.__dict__)

rows = json.loads((ROOT / "docs/final-evaluation-20261025/full200-results.json").read_text(encoding="utf-8"))["results"]
wrong = [r for r in rows if r["evaluation_label"] == "incorrect_refusal_evidence_exists"]
flipped = []
for row in wrong:
    before, _ = run(row, False)
    after, answer = run(row, True)
    mark = "FLIPS" if after == "ANSWERED" and before != "ANSWERED" else ""
    print(f"{row['id']:5} before: {before[:55]:55} | after: {after[:55]:55} {mark}")
    if mark:
        flipped.append((row["id"], row["question"], answer))
print(f"\n{len(flipped)} of {len(wrong)} would be answered")
for case, question, answer in flipped:
    print(f"\n{case} {question}\n  {answer}")
