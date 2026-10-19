"""Resumable local-Ollama spot check after reliability changes."""

from __future__ import annotations

import importlib.util
import json
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RESULTS = HERE / "results.json"
PRIOR = ROOT / "docs/grounding-30-final-20261016-180507/run_30.py"
BASELINE = ROOT / "docs/full-200-ceng-ai-advisor-evaluation-after-kb-ollama-20261013-202801/results.json"
IDS = (
    "F001", "C019", "C020", "M032", "P056", "H063", "A075", "Y090",
    "R108", "R120", "S129", "X141", "T184", "T187", "T188", "T189",
    "U153", "O166", "N001", "N002", "N003", "N004", "N005", "N006",
)

spec = importlib.util.spec_from_file_location("prior_grounding_run", PRIOR)
if spec is None or spec.loader is None:
    raise RuntimeError("Cannot load the previous case selector")
prior = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prior)
evaluation = prior.evaluation
case_by_id = {case["id"]: case for case in prior.cases()}
selected = [case_by_id[case_id] for case_id in IDS]
before = {row["id"]: row for row in json.loads(BASELINE.read_text(encoding="utf-8"))["results"]}


def save(records: list[dict], complete: bool) -> None:
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "complete": complete,
        "case_count": len(records),
        "selected_ids": list(IDS),
        "summary": evaluation.summarize(records),
        "results": records,
    }
    temporary = RESULTS.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(RESULTS)


def main() -> None:
    records = json.loads(RESULTS.read_text(encoding="utf-8"))["results"] if RESULTS.exists() else []
    done = {record["id"] for record in records}
    pipeline = evaluation.RAGPipeline()
    for index, case in enumerate(selected, start=1):
        if case["id"] in done:
            continue
        print(f"case {index:02d}/{len(selected)} {case['id']}", flush=True)
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
                "elapsed_wall_seconds": round(time.perf_counter() - started, 3),
                "diagnostics": diagnostics,
                "answer": result.get("answer"),
                "sources": result.get("sources") or [],
                "retrieved_context": evaluation.compact_context(result.get("retrieved_context") or []),
                "previous_turn_setup": None if not previous_result else {
                    "question": case.get("previous_question"),
                    "status": previous_result.get("status"),
                    "answer": previous_result.get("answer"),
                },
            }
        except Exception as exc:
            record = {
                **case,
                "evaluation_label": "runtime_error",
                "baseline_label": before[case["id"]]["evaluation_label"] if case["id"] in before else None,
                "elapsed_wall_seconds": round(time.perf_counter() - started, 3),
                "diagnostics": {"status": "error", "error": repr(exc)},
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
