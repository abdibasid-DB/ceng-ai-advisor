"""Run the complete local Stage 15 RAG pipeline from the command line."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.rag.rag_pipeline import RAGPipeline


TEST_CASES_PATH = PROJECT_ROOT / "tests" / "rag_test_cases.json"
DEFAULT_OUTPUT_PATH = PROJECT_ROOT / "docs" / "rag-live-test-results.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_test_cases() -> list[dict]:
    with TEST_CASES_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)["cases"]


def compact_result(result: dict) -> dict:
    return {
        "question": result["question"],
        "status": result["status"],
        "answer": result["answer"],
        "llm_called": result["llm_called"],
        "sources": result["sources"],
        "retrieved_chunks": [
            {
                "label": item.get("label"),
                "chunk_id": item["chunk_id"],
                "source_id": item["source_id"],
                "title": item["title"],
                "category": item["category"],
                "similarity_score": item["similarity_score"],
                "url": item["url"],
                "passage_preview": item.get("passage", item.get("text", ""))[:500],
            }
            for item in result["retrieved_context"]
        ],
        "retrieval_metadata": result["retrieval_metadata"],
        "timing": result["timing"],
        "error": result["error"],
        "answer_warnings": result.get("answer_warnings", []),
        "citation_metadata": result.get("citation_metadata", {}),
    }


def run_question(question: str) -> dict:
    return compact_result(RAGPipeline().answer(question))


def run_preset(limit: int | None = None, ids: set[str] | None = None, output_path: Path = DEFAULT_OUTPUT_PATH) -> dict:
    pipeline = RAGPipeline()
    cases = load_test_cases()
    if ids:
        cases = [case for case in cases if case["id"] in ids]
    if limit is not None:
        cases = cases[:limit]
    results = []
    for case in cases:
        result = compact_result(pipeline.answer(case["question"]))
        result["id"] = case["id"]
        result["type"] = case["type"]
        results.append(result)
    output = {
        "stage": "Stage 15/15B - Core RAG Pipeline Validation",
        "generated_at": utc_now(),
        "case_count": len(results),
        "results": results,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="\n") as file:
        json.dump(output, file, ensure_ascii=False, indent=2)
        file.write("\n")
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Test the complete local RAG pipeline.")
    parser.add_argument("question", nargs="?", help="Question to run through the RAG pipeline.")
    parser.add_argument("--preset", action="store_true", help="Run the representative Stage 15 test set.")
    parser.add_argument("--limit", type=int, default=None, help="Limit preset cases for quicker smoke tests.")
    parser.add_argument("--ids", nargs="*", default=None, help="Run only selected preset case IDs.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH), help="Where to write preset JSON results.")
    args = parser.parse_args()

    if args.preset:
        selected_ids = set(args.ids) if args.ids else None
        print(json.dumps(run_preset(args.limit, selected_ids, Path(args.output)), indent=2, ensure_ascii=False))
        return
    if not args.question:
        parser.error("question is required unless --preset is used")
    print(json.dumps(run_question(args.question), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
