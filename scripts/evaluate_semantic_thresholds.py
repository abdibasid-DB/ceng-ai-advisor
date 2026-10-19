"""Offline replay for choosing the semantic grounding thresholds.

Replays a saved full-200 results file through embedding-similarity checks
without calling Ollama:

(a) question <-> answer similarity (rescue for the topic-term coverage check)
(b) cited sentence <-> best-matching sentence in the cited passage

For each candidate threshold it reports how many known-good answers/claims
reach it, how many known-unsupported ones would also reach it, and how often
unrelated (mismatched) pairs reach it. Lexical checks are replayed with the
semantic encoder disabled, so they show the pipeline's word-overlap behaviour.

Usage:
    python scripts/evaluate_semantic_thresholds.py RESULTS_JSON [--trace TRACE_JSON] [--output OUT_JSON]
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

import numpy as np  # noqa: E402
from sentence_transformers import SentenceTransformer  # noqa: E402

from backend.app.core.retrieval_config import EMBEDDING_MODEL_NAME  # noqa: E402
from backend.app.rag import rag_pipeline as rp  # noqa: E402

QUESTION_ANSWER_CANDIDATES = (0.55, 0.60, 0.65)
SENTENCE_PASSAGE_CANDIDATES = (0.60, 0.65, 0.70)
NO_EVIDENCE_PREFIX = "The retrieved evidence does not establish"

_model: SentenceTransformer | None = None
_cache: dict[str, np.ndarray] = {}


def embed(texts: list[str]) -> np.ndarray:
    global _model
    if _model is None:
        _model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    missing = [text for text in dict.fromkeys(texts) if text not in _cache]
    if missing:
        vectors = _model.encode(missing, normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=False)
        _cache.update(zip(missing, vectors))
    return np.stack([_cache[text] for text in texts])


def similarity(first: str, second: str) -> float:
    return float(embed([first])[0] @ embed([second])[0])


def clean(text: str) -> str:
    return " ".join(rp.strip_citation_text(text).split())


def best_sentence_similarity(claim: str, passage: str) -> float:
    sentences = rp.passage_sentences(passage)
    if not sentences:
        return 0.0
    return float((embed(sentences) @ embed([claim])[0]).max())


def gate_question(case: dict) -> str:
    return rp.strip_retrieval_annotations(case["diagnostics"].get("resolved_question") or case["question"])


def question_answer_record(case: dict, answer: str | None = None) -> dict:
    answer = case["answer"] if answer is None else answer
    question = gate_question(case)
    return {
        "id": case["id"],
        "label": case["evaluation_label"],
        "lexical_reason": rp.unsupported_generated_answer_reason(question, answer, case.get("retrieved_context") or []),
        "similarity": similarity(question, clean(answer)),
    }


def claim_records(case: dict) -> list[dict]:
    context = {item.get("label"): item for item in case.get("retrieved_context") or []}
    records = []
    for check in case["diagnostics"]["support_check"].get("checks") or []:
        claim = check["claim"]
        labels = [label for label in rp.extract_citation_labels(claim) if label in context]
        labels = labels or [label for label in check.get("labels") or [] if label in context]
        if not labels:
            continue
        records.append({
            "id": case["id"],
            "label": case["evaluation_label"],
            "evaluator_supported": check.get("supported"),
            "lexical_pass": any(rp.cited_claim_supported(claim, context[label]) for label in labels),
            "similarity": max(best_sentence_similarity(clean(claim), context[label].get("passage") or "") for label in labels),
            "claim": claim[:200],
        })
    return records


def replay(results_path: Path, trace_path: Path | None) -> dict:
    rp.configure_semantic_encoder(None)
    cases = json.loads(results_path.read_text(encoding="utf-8"))["results"]
    by_label: dict[str, list[dict]] = {}
    for case in cases:
        by_label.setdefault(case["evaluation_label"], []).append(case)
    correct = by_label.get("correct_evidence_supported", [])
    unsupported = by_label.get("unsupported_incorrect_or_misleading", [])
    refusals = by_label.get("incorrect_refusal_evidence_exists", [])
    rng = random.Random(42)

    answered = [case for case in cases if case["diagnostics"]["status"] == "answered"]
    qa_mismatched = []
    for case in answered:
        others = [other for other in answered if other["group"] != case["group"]]
        for other in rng.sample(others, min(5, len(others))):
            qa_mismatched.append(similarity(gate_question(case), clean(other["answer"])))

    claim_mismatched = []
    for case in correct:
        others = [other for other in correct if other["group"] != case["group"]]
        for check in (case["diagnostics"]["support_check"].get("checks") or [])[:3]:
            passages = [item.get("passage") or "" for item in rng.choice(others).get("retrieved_context") or []]
            if passages:
                claim_mismatched.append(max(best_sentence_similarity(clean(check["claim"]), p) for p in passages))

    output = {
        "replayability": {
            "refused_before_llm": [c["id"] for c in refusals if not c["diagnostics"]["llm_called"]],
            "llm_called_with_saved_generation": [
                c["id"] for c in refusals
                if c["diagnostics"]["llm_called"] and (c["diagnostics"].get("retrieval_metadata") or {}).get("discarded_generation")
            ],
            "llm_called_without_saved_generation": [
                c["id"] for c in refusals
                if c["diagnostics"]["llm_called"] and not (c["diagnostics"].get("retrieval_metadata") or {}).get("discarded_generation")
            ],
        },
        "question_answer": {
            "correct": [question_answer_record(c) for c in correct],
            "unsupported": [question_answer_record(c) for c in unsupported],
            "mismatched": qa_mismatched,
        },
        "sentence_passage": {
            "correct": [r for c in correct for r in claim_records(c)],
            "unsupported": [r for c in unsupported for r in claim_records(c)],
            "mismatched": claim_mismatched,
        },
    }
    for case in refusals:
        saved = (case["diagnostics"].get("retrieval_metadata") or {}).get("discarded_generation")
        if saved:
            output["question_answer"].setdefault("replayed_refusals", []).append(question_answer_record(case, saved))

    if trace_path:
        traces = json.loads(trace_path.read_text(encoding="utf-8"))
        by_question = {case["question"].strip().lower(): case for case in cases}
        for trace in traces:
            case = by_question.get(trace["question"].strip().lower())
            if case:
                output["question_answer"].setdefault("traces", []).append(question_answer_record(case, trace["raw"]))
    return output


def print_tables(output: dict) -> None:
    replayable = output["replayability"]
    print("Replayability of incorrect refusals:")
    for key, ids in replayable.items():
        print(f"  {key}: {len(ids)}")

    qa = output["question_answer"]
    print("\n(a) question-answer similarity")
    print("threshold | correct >= t | unsupported >= t | mismatched >= t")
    for t in QUESTION_ANSWER_CANDIDATES:
        good = sum(r["similarity"] >= t for r in qa["correct"])
        bad = [r["id"] for r in qa["unsupported"] if r["similarity"] >= t]
        mismatch = sum(s >= t for s in qa["mismatched"])
        print(f"{t:.2f} | {good}/{len(qa['correct'])} | {len(bad)}/{len(qa['unsupported'])} {bad} | {mismatch}/{len(qa['mismatched'])}")

    sp = output["sentence_passage"]
    flagged = [r for r in sp["unsupported"] if not r["evaluator_supported"] and not r["claim"].startswith(NO_EVIDENCE_PREFIX)]
    print("\n(b) sentence-passage similarity")
    print("threshold | correct claims >= t | flagged unsupported claims >= t | mismatched >= t")
    for t in SENTENCE_PASSAGE_CANDIDATES:
        good = sum(r["similarity"] >= t for r in sp["correct"])
        bad = [r["id"] for r in flagged if r["similarity"] >= t]
        mismatch = sum(s >= t for s in sp["mismatched"])
        print(f"{t:.2f} | {good}/{len(sp['correct'])} | {len(bad)}/{len(flagged)} {bad} | {mismatch}/{len(sp['mismatched'])}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("results", type=Path, help="results.json from a full-200 evaluation run")
    parser.add_argument("--trace", type=Path, help="optional trace JSON with raw generations ({question, raw})")
    parser.add_argument("--output", type=Path, help="write detailed per-case scores to this JSON file")
    args = parser.parse_args()
    output = replay(args.results, args.trace)
    if args.output:
        args.output.write_text(json.dumps(output, ensure_ascii=False, indent=1), encoding="utf-8")
    print_tables(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
