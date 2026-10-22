"""Part 2 rule check: does the live retriever now find the passage each hand-written function supplied?

For every hand-written passage function in rag_pipeline.py, all test-set
questions that trigger it are retrieved with the live retriever (top 5, no
augmentation). A question counts as covered when a retrieved chunk from the
function's source contains the function's key source text. The function is
deleted when every triggering question is covered; otherwise its source text
becomes a curated source note.

Usage: python docs/handwritten-removal-20261022/check_passages.py [OUTPUT_NAME]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.rag.retriever import Retriever  # noqa: E402

# function -> (source_id, key source texts; a chunk must contain one of them)
FUNCTIONS = {
    "programming_languages_passage": ("src_004", ["object-oriented languages such as python or c++"]),
    "gpa_screening_passage": ("src_033", ["gpa as a candidate screening tool has fallen into disfavor"]),
    "computer_engineering_definition_passage": ("src_042", ["computer engineering involves"]),
    "future_technologies_passage": ("src_063", ["quantum computing", "microservices architecture", "blockchain technology"]),
    "linux_operating_system_passage": ("src_004", ["linux or windows"]),
    "specialization_areas_passage": ("src_043", ["specialization areas in computer engineering"]),
}


# Curated source notes that replaced each function (build_curated_notes.py); counted once they exist.
CURATED = {
    "programming_languages_passage": "src_126",
    "gpa_screening_passage": "src_127",
    "computer_engineering_definition_passage": "src_128",
    "future_technologies_passage": "src_129",
    "linux_operating_system_passage": "src_130",
    "specialization_areas_passage": "src_131",
}


def load(path: Path):
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def test_questions() -> list[dict[str, str]]:
    tests = ROOT / "tests"
    questions = [{"set": "full_200", "id": c["id"], "question": c["question"]} for c in load(ROOT / "docs" / "semantic-coverage-200-questions.json")["cases"]]
    questions += [{"set": "comprehensive", "id": c["id"], "question": c["question"]} for c in load(tests / "rag_comprehensive_evaluation_cases.json")["cases"]]
    questions += [{"set": "paraphrase", "id": c["id"], "question": c["question"]} for c in load(tests / "retrieval_paraphrase_cases.json")]
    questions += [{"set": "unseen", "id": c["id"], "question": c["question"]} for c in load(tests / "unseen_coverage_cases.json")]
    questions += [{"set": "rag_test", "id": c["id"], "question": c["question"]} for c in load(tests / "rag_test_cases.json")["cases"]]
    questions += [{"set": "retrieval_test", "id": c["id"], "question": c["question"]} for c in load(tests / "retrieval_test_cases.json")["cases"]]
    seen: dict[str, dict[str, str]] = {}
    for item in questions:
        seen.setdefault(" ".join(item["question"].lower().split()), item)
    return list(seen.values())


def main() -> int:
    retriever = Retriever()
    # Triggering questions were recorded with the original detectors before the functions were removed.
    questions = json.loads((HERE / "questions.json").read_text(encoding="utf-8"))
    report = {}
    for name, (source_id, needles) in FUNCTIONS.items():
        rows = []
        for item in questions:
            if name not in item["built_for"]:
                continue
            results = retriever.retrieve(item["question"], top_k=5)["results"]
            hit = next(
                (r["chunk_id"] for r in results if r["source_id"] in {source_id, CURATED.get(name)} and any(n in r["text"].lower() for n in needles)),
                None,
            )
            rows.append({**item, "covered_by": hit, "top5": [r["chunk_id"] for r in results]})
        covered = sum(1 for row in rows if row["covered_by"])
        decision = "delete" if rows and covered == len(rows) else "curated_source_note"
        report[name] = {"source_id": source_id, "key_text": needles, "questions": len(rows), "covered": covered, "decision": decision, "rows": rows}
        print(f"{name}: {covered}/{len(rows)} triggering questions have the passage in the top 5 -> {decision}")
        for row in rows:
            if not row["covered_by"]:
                print(f"    missing: [{row['set']} {row['id']}] {row['question']}")
    output = HERE / (sys.argv[1] if len(sys.argv) > 1 else "passage-check.json")
    output.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
