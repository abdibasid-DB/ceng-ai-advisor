"""Resumable live 30-case grounding check against the current local RAG pipeline."""

from __future__ import annotations

import importlib.util
import json
import time
from datetime import datetime, timezone
from pathlib import Path

ARTIFACT_DIR = Path(__file__).resolve().parent
ROOT = ARTIFACT_DIR.parents[1]
RESULTS = ARTIFACT_DIR / "results.json"
BASELINE = ROOT / "docs/full-200-ceng-ai-advisor-evaluation-after-kb-ollama-20261013-202801"

spec = importlib.util.spec_from_file_location("full_200_evaluator", BASELINE / "run_full_200_evaluation.py")
if spec is None or spec.loader is None:
    raise RuntimeError("Could not load the existing evaluation runner")
evaluation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(evaluation)

EXISTING_IDS = (
    "F001", "C019", "C020", "M032", "P045", "P056", "H063", "A075",
    "Y088", "Y090", "R108", "R120", "S126", "S129", "X141", "X151",
    "T184", "T187", "T188", "T189", "T193", "T200", "U153", "O166",
)

UNSEEN = (
    ("N001", "How do databases and operating systems fit into Computer Engineering?", "programming_software", ("software", "operating_systems"), ("software_development", "curriculum"), "answer_or_gap"),
    ("N002", "Can I build an FPGA project before taking digital logic?", "hardware_networks", ("hardware", "projects"), ("hardware_and_embedded_systems",), "answer_or_gap"),
    ("N003", "Does studying AI in CENG require linear algebra and probability?", "ai_future", ("ai", "mathematics"), ("ai_and_data_science", "curriculum"), "answer_or_gap"),
    ("N004", "What can a first-year student put in a GitHub portfolio for internships?", "career_employment", ("projects", "internships"), ("career_opportunities", "professional_development"), "answer_or_gap"),
    ("N005", "Does OSTIM Technical University guarantee a remote job abroad after graduation?", "unsupported", ("remote_work", "career"), (), "insufficient"),
    ("N006", "My teammate and I built an embedded sensor project. How should I explain my own contribution to employers?", "career_employment", ("projects", "career"), ("professional_development",), "answer_or_gap"),
)


def cases() -> list[dict]:
    existing = {row["id"]: row for row in evaluation.load_cases()}
    selected = [existing[case_id] for case_id in EXISTING_IDS]
    selected.extend(
        {
            "id": case_id,
            "question": question,
            "group": group,
            "expected_topics": list(topics),
            "expected_categories": list(categories),
            "expected_behavior": behavior,
            "previous_question": None,
            "unseen": True,
        }
        for case_id, question, group, topics, categories, behavior in UNSEEN
    )
    if len(selected) != 30 or len({row["id"] for row in selected}) != 30:
        raise RuntimeError("Expected 30 unique cases")
    return selected


def save(records: list[dict], complete: bool) -> None:
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "complete": complete,
        "case_count": len(records),
        "selected_ids": [row["id"] for row in cases()],
        "summary": evaluation.summarize(records),
        "results": records,
    }
    temp = RESULTS.with_suffix(".json.tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(RESULTS)


def main() -> None:
    selected = cases()
    previous = json.loads((BASELINE / "results.json").read_text(encoding="utf-8"))
    before = {row["id"]: row for row in previous["results"]}
    records = json.loads(RESULTS.read_text(encoding="utf-8"))["results"] if RESULTS.exists() else []
    done = {row["id"] for row in records}
    pipeline = evaluation.RAGPipeline()

    for index, case in enumerate(selected, start=1):
        if case["id"] in done:
            continue
        print(f"case {index:02d}/30 {case['id']}", flush=True)
        started = time.perf_counter()
        previous_result = None
        try:
            previous_turn = None
            if case.get("previous_question"):
                previous_result, _ = evaluation.run_backend_question(pipeline, case["previous_question"], None)
                previous_turn = evaluation.previous_turn_from_result(case["previous_question"], previous_result)
            result, resolution = evaluation.run_backend_question(pipeline, case["question"], previous_turn)
            label, diagnostics = evaluation.classify_case(case, result, resolution)
            record = {
                **case,
                "evaluation_label": label,
                "baseline_label": before[case["id"]]["evaluation_label"] if case["id"] in before else None,
                "baseline_status": before[case["id"]]["diagnostics"]["status"] if case["id"] in before else None,
                "elapsed_wall_seconds": round(time.perf_counter() - started, 3),
                "diagnostics": diagnostics,
                "answer": result.get("answer"),
                "sources": result.get("sources") or [],
                "retrieved_context": evaluation.compact_context(result.get("retrieved_context") or []),
                "previous_turn_setup": None if not previous_result else {
                    "question": case.get("previous_question"),
                    "status": previous_result.get("status"),
                    "answer": previous_result.get("answer"),
                    "sources": previous_result.get("sources") or [],
                },
            }
        except Exception as exc:
            record = {
                **case,
                "evaluation_label": "runtime_error",
                "baseline_label": before[case["id"]]["evaluation_label"] if case["id"] in before else None,
                "baseline_status": before[case["id"]]["diagnostics"]["status"] if case["id"] in before else None,
                "elapsed_wall_seconds": round(time.perf_counter() - started, 3),
                "diagnostics": {"status": "error", "error": repr(exc), "evidence_exists_by_eval": False, "citation_valid": False, "support_check": {}, "retrieval_metadata": {}, "timing": {}},
                "answer": None,
                "sources": [],
                "retrieved_context": [],
                "previous_turn_setup": None,
            }
        records.append(record)
        save(records, complete=False)
    save(records, complete=True)
    print(json.dumps(evaluation.summarize(records), indent=2), flush=True)


if __name__ == "__main__":
    main()
