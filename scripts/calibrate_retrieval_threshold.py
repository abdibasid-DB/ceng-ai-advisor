"""Calibrate the retrieval evidence gate (MIN_SIMILARITY_THRESHOLD) for a new embedding model.

The gate in backend/app/rag/retriever.py refuses a question when the top
retrieved chunk's cosine similarity is below MIN_SIMILARITY_THRESHOLD or
fewer than MIN_RESULTS_ABOVE_THRESHOLD of the top-k chunks reach it.

This script retrieves every in-scope and every out-of-scope/insufficient test
question with the live retriever and, for reference, with the previous index
(all-MiniLM-L6-v2, vector-only, threshold 0.30) restored from a backup. For
each candidate threshold it reports the share of in-scope questions that pass
and the share of out-of-scope/insufficient questions that are blocked.

Decision rule: at least 95% of in-scope questions must pass; among those
thresholds, choose the one that blocks the most out-of-scope/insufficient
questions, which must be at least as many as the previous gate blocked.

Usage:
    python scripts/calibrate_retrieval_threshold.py --old-chroma D:/ceng-backup-20261022-pre-option-f/vector_store/chroma [--output OUT_JSON]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.core.retrieval_config import DEFAULT_TOP_K, MIN_RESULTS_ABOVE_THRESHOLD  # noqa: E402
from backend.app.rag.retriever import Retriever  # noqa: E402

OLD_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
OLD_THRESHOLD = 0.30
IN_SCOPE_PASS_TARGET = 0.95
CANDIDATES = [round(0.30 + 0.01 * step, 2) for step in range(31)]


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def load_questions() -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """(in_scope, out_of_scope_or_insufficient) questions from the test sets, deduplicated by text."""
    tests = PROJECT_ROOT / "tests"
    in_scope: list[dict[str, str]] = []
    refuse: list[dict[str, str]] = []

    for case in load_json(PROJECT_ROOT / "docs" / "semantic-coverage-200-questions.json")["cases"]:
        # Multi-turn follow-ups depend on the previous turn and are resolved before retrieval.
        if case["previous_question"]:
            continue
        target = in_scope if case["expected_behavior"] == "answer_or_gap" else refuse
        target.append({"set": "full_200", "id": case["id"], "question": case["question"]})
    for case in load_json(tests / "retrieval_paraphrase_cases.json"):
        in_scope.append({"set": "paraphrase", "id": case["id"], "question": case["question"]})
    for case in load_json(tests / "unseen_coverage_cases.json"):
        target = in_scope if case["expected_behavior"] == "answer" else refuse
        target.append({"set": "unseen", "id": case["id"], "question": case["question"]})
    for case in load_json(tests / "retrieval_test_cases.json")["cases"]:
        target = refuse if case["type"] == "out_of_scope" else in_scope
        target.append({"set": "retrieval_test", "id": case["id"], "question": case["question"]})
    for case in load_json(tests / "rag_test_cases.json")["cases"]:
        target = refuse if case["type"] in {"out_of_scope", "unsupported_in_domain"} else in_scope
        target.append({"set": "rag_test", "id": case["id"], "question": case["question"]})
    for case in load_json(tests / "rag_comprehensive_evaluation_cases.json")["cases"]:
        if case["expected_behavior"] == "answer":
            in_scope.append({"set": "comprehensive", "id": case["id"], "question": case["question"]})

    def dedupe(items: list[dict[str, str]]) -> list[dict[str, str]]:
        seen: dict[str, dict[str, str]] = {}
        for item in items:
            seen.setdefault(" ".join(item["question"].lower().split()), item)
        return list(seen.values())

    return dedupe(in_scope), dedupe(refuse)


class OldRetriever(Retriever):
    """The previous live setup: MiniLM (256 tokens), vector-only, 384 dimensions."""

    def get_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name)
        return self._model

    def encode_query(self, query: str) -> list[float]:
        vector = self.get_model().encode([self._clean_query(query)], normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=False)[0]
        return vector.astype(float).tolist()


def similarities(retriever: Retriever, questions: list[dict[str, str]]) -> list[dict[str, Any]]:
    rows = []
    for item in questions:
        results = retriever.retrieve(item["question"], top_k=DEFAULT_TOP_K)["results"]
        rows.append({**item, "similarities": [round(result["similarity_score"], 4) for result in results]})
    return rows


def passes(row: dict[str, Any], threshold: float) -> bool:
    scores = row["similarities"]
    return bool(scores) and scores[0] >= threshold and sum(score >= threshold for score in scores) >= MIN_RESULTS_ABOVE_THRESHOLD


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--old-chroma", type=Path, required=True, help="Chroma folder of the previous MiniLM index (backup)")
    parser.add_argument("--output", type=Path, help="write per-question similarities and the table to this JSON file")
    args = parser.parse_args()

    in_scope, refuse = load_questions()
    print(f"in-scope questions: {len(in_scope)}; out-of-scope/insufficient questions: {len(refuse)}")

    old = OldRetriever(chroma_path=args.old_chroma, model_name=OLD_MODEL, hybrid=False)
    old_in, old_out = similarities(old, in_scope), similarities(old, refuse)
    old_pass = sum(passes(row, OLD_THRESHOLD) for row in old_in) / len(old_in)
    old_blocked = sum(not passes(row, OLD_THRESHOLD) for row in old_out)
    print(f"previous gate (MiniLM, {OLD_THRESHOLD}): in-scope pass {old_pass:.3f}, refuse-set blocked {old_blocked}/{len(old_out)}")

    live = Retriever()
    new_in, new_out = similarities(live, in_scope), similarities(live, refuse)
    table = []
    print("threshold | in-scope pass | refuse-set blocked")
    for threshold in CANDIDATES:
        pass_rate = sum(passes(row, threshold) for row in new_in) / len(new_in)
        blocked = sum(not passes(row, threshold) for row in new_out)
        table.append({"threshold": threshold, "in_scope_pass_rate": round(pass_rate, 4), "refuse_set_blocked": blocked})
        print(f"{threshold:.2f} | {pass_rate:.3f} | {blocked}/{len(new_out)}")

    eligible = [row for row in table if row["in_scope_pass_rate"] >= IN_SCOPE_PASS_TARGET]
    chosen = max(eligible, key=lambda row: (row["refuse_set_blocked"], -row["threshold"])) if eligible else None
    if chosen:
        verdict = "meets both rules" if chosen["refuse_set_blocked"] >= old_blocked else "meets the 95% rule only; blocks fewer than before"
        print(f"chosen threshold {chosen['threshold']:.2f}: {verdict}")

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(
                {
                    "previous": {"model": OLD_MODEL, "threshold": OLD_THRESHOLD, "in_scope_pass_rate": round(old_pass, 4), "refuse_set_blocked": old_blocked},
                    "refuse_set_size": len(refuse),
                    "table": table,
                    "chosen": chosen,
                    "new_in_scope": new_in,
                    "new_refuse_set": new_out,
                    "old_refuse_set": old_out,
                },
                ensure_ascii=False,
                indent=1,
            ),
            encoding="utf-8",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
