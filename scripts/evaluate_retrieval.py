"""Run Stage 13 qualitative retrieval evaluation.

This script evaluates retrieval only. It does not generate chatbot answers,
construct prompts, call Ollama, or implement RAG.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.rag.retriever import Retriever


TEST_CASES_PATH = PROJECT_ROOT / "tests" / "retrieval_test_cases.json"
OUTPUT_PATH = PROJECT_ROOT / "docs" / "retrieval-evaluation-results.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def classify_result(result: dict[str, Any], expected_categories: list[str], case_type: str) -> str:
    categories = [item["category"] for item in result["results"]]
    top_similarity = result["top_similarity_score"]
    matched = sum(1 for category in categories if category in expected_categories)

    if case_type == "out_of_scope":
        return "Correctly rejected" if result["out_of_scope"] else "False positive"

    if matched >= 2 and result["evidence_sufficient"] and top_similarity >= 0.45:
        return "Highly relevant"
    if matched >= 1 and result["evidence_sufficient"]:
        return "Relevant"
    if matched >= 1:
        return "Partially relevant"
    return "Irrelevant"


def evaluate(top_k: int) -> dict[str, Any]:
    test_data = load_json(TEST_CASES_PATH)
    retriever = Retriever()
    evaluated_cases = []

    for case in test_data["cases"]:
        retrieval = retriever.retrieve(case["question"], top_k=top_k)
        expected_categories = case.get("expected_categories", [])
        label = classify_result(retrieval, expected_categories, case["type"])
        evaluated_cases.append(
            {
                "id": case["id"],
                "type": case["type"],
                "category": case["category"],
                "question": case["question"],
                "expected_categories": expected_categories,
                "label": label,
                "evidence_sufficient": retrieval["evidence_sufficient"],
                "out_of_scope": retrieval["out_of_scope"],
                "top_similarity_score": retrieval["top_similarity_score"],
                "results_above_threshold": retrieval["results_above_threshold"],
                "top_results": [
                    {
                        "rank": item["rank"],
                        "chunk_id": item["chunk_id"],
                        "source_id": item["source_id"],
                        "category": item["category"],
                        "title": item["title"],
                        "similarity_score": item["similarity_score"],
                        "rerank_score": item["rerank_score"],
                    }
                    for item in retrieval["results"]
                ],
            }
        )

    label_counts: dict[str, int] = {}
    for item in evaluated_cases:
        label_counts[item["label"]] = label_counts.get(item["label"], 0) + 1

    output = {
        "stage": "Stage 13 - Retrieval Pipeline and Retrieval Quality",
        "generated_at": utc_now(),
        "top_k": top_k,
        "test_case_count": len(evaluated_cases),
        "label_counts": label_counts,
        "cases": evaluated_cases,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8", newline="\n") as file:
        json.dump(output, file, ensure_ascii=False, indent=2)
        file.write("\n")

    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate Stage 13 retrieval quality.")
    parser.add_argument("--top-k", type=int, default=5, help="Number of final retrieval results per question.")
    args = parser.parse_args()
    print(json.dumps(evaluate(args.top_k), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
