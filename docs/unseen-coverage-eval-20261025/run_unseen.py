"""End-to-end evaluation of the unseen student questions (2026-10-25, evaluation only).

Runs the 116 "answer" and 4 "insufficient" cases of tests/unseen_coverage_cases.json
through the live pipeline, on the same backend path as the final evaluation
(query understanding, LLM follow-up rewrite, RAGPipeline), and labels them with
the official full-200 classifier (docs/full-200-ceng-ai-advisor-evaluation-after-kb-ollama-20261013-202801).

The unseen cases name expected sources, not categories. The classifier's
evidence check uses categories, so each case gets the registry categories of
its expected sources as `expected_categories`; "answer" maps to the
classifier's "answer_or_gap". Whether an expected source is among the
retrieved passages is reported separately.

Steps: run (resumable), report.

Usage: python docs/unseen-coverage-eval-20261025/run_unseen.py run report
"""

from __future__ import annotations

import importlib.util
import json
import shutil
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from backend.app.core.storage_config import ensure_disk_space, prepare_evaluation_storage  # noqa: E402

OUTPUT_DIR = prepare_evaluation_storage("unseen-coverage-eval-20261025")
RESULTS = OUTPUT_DIR / "results.json"
LABELS = [
    "correct_evidence_supported",
    "correct_insufficient_information",
    "incorrect_refusal_evidence_exists",
    "unsupported_incorrect_or_misleading",
    "runtime_error",
]

spec = importlib.util.spec_from_file_location("run_spec_fix", ROOT / "docs" / "spec-fix-20261023" / "run_spec_fix.py")
spec_fix = importlib.util.module_from_spec(spec)
spec.loader.exec_module(spec_fix)


def load_cases() -> list[dict]:
    categories = {source["source_id"]: source["category"] for source in json.loads((ROOT / "knowledge_base" / "sources.json").read_text(encoding="utf-8"))["sources"]}
    cases = []
    for case in json.loads((ROOT / "tests" / "unseen_coverage_cases.json").read_text(encoding="utf-8")):
        cases.append({
            "id": case["id"],
            "question": case["question"],
            "group": case["topic_area"],
            "expected_topics": [],
            "expected_categories": sorted({categories[source_id] for source_id in case["expected_source_ids"] if source_id in categories}),
            "expected_source_ids": case["expected_source_ids"],
            "expected_behavior": "answer_or_gap" if case["expected_behavior"] == "answer" else case["expected_behavior"],
            "unseen_expected_behavior": case["expected_behavior"],
            "previous_question": None,
        })
    return cases


def step_run() -> None:
    runner = spec_fix.load_runner(ROOT)
    pipeline = runner.RAGPipeline()
    cases = load_cases()
    rows = json.loads(RESULTS.read_text(encoding="utf-8")) if RESULTS.exists() else []
    done = {row["id"] for row in rows}
    for number, case in enumerate(cases, start=1):
        if case["id"] in done:
            continue
        rows.append(spec_fix.run_case(runner, pipeline, case))
        RESULTS.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"{number}/{len(cases)} {case['id']} {rows[-1]['evaluation_label']} {rows[-1]['elapsed_wall_seconds']} s", flush=True)
        ensure_disk_space()
    print(f"wrote {RESULTS}")


def refusing_gate(row: dict) -> str:
    """Name the pipeline stage that produced a refusal, from the recorded diagnostics."""
    diagnostics = row["diagnostics"]
    metadata = diagnostics.get("retrieval_metadata") or {}
    reason = metadata.get("unsupported_reason") or ""
    if diagnostics["status"] == "out_of_scope" or metadata.get("out_of_scope"):
        return "query understanding: out of scope"
    if metadata.get("evidence_sufficient") is False:
        return "evidence gate: similarity below threshold"
    if not diagnostics.get("llm_called"):
        return f"answerability guard (before the LLM): {reason or 'no reason recorded'}"
    if "distinctive topic terms" in reason:
        return f"generated-answer topic check: {reason}"
    if metadata.get("discarded_generation") is not None or reason:
        return f"citation / claim validation after generation: {reason or 'no reason recorded'}"
    return "model answered INSUFFICIENT_INFORMATION"


def expected_source_retrieved(row: dict) -> bool:
    return bool(set(row["expected_source_ids"]) & {item["source_id"] for item in row.get("retrieved_context") or []})


def summary(rows: list[dict]) -> dict:
    labels = Counter(row["evaluation_label"] for row in rows)
    times = [row["elapsed_wall_seconds"] for row in rows]
    return {
        "n": len(rows),
        **{label: labels.get(label, 0) for label in LABELS},
        "expected_source_retrieved": sum(expected_source_retrieved(row) for row in rows),
        "mean_seconds": round(statistics.mean(times), 1) if times else None,
    }


def pct(count: int, total: int) -> str:
    return f"{count} ({100 * count / total:.1f}%)" if total else "0"


def step_report() -> None:
    rows = json.loads(RESULTS.read_text(encoding="utf-8"))
    answer_rows = [row for row in rows if row["unseen_expected_behavior"] == "answer"]
    insufficient_rows = [row for row in rows if row["unseen_expected_behavior"] == "insufficient"]
    by_topic: dict[str, list[dict]] = defaultdict(list)
    for row in answer_rows:
        by_topic[row["group"]].append(row)
    result = {
        "answer_cases": summary(answer_rows),
        "insufficient_cases": summary(insufficient_rows),
        "by_topic_answer_cases": {topic: summary(items) for topic, items in sorted(by_topic.items())},
        "wrongly_refused": [
            {"id": row["id"], "topic": row["group"], "question": row["question"], "gate": refusing_gate(row), "expected_source_retrieved": expected_source_retrieved(row)}
            for row in rows if row["evaluation_label"] == "incorrect_refusal_evidence_exists"
        ],
    }
    (OUTPUT_DIR / "summary.json").write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")

    a = result["answer_cases"]
    n = a["n"]
    lines = [
        "# Unseen student questions, end to end (2026-10-25)",
        "",
        "Evaluation only; no code was changed. The 120 cases of tests/unseen_coverage_cases.json (116 \"answer\", 4 \"insufficient\") were run "
        "through the live pipeline of the frozen system (tag `frozen-20261025`) and labelled with the official full-200 classifier. "
        "Each case's `expected_categories` are the registry categories of its expected sources (see [run_unseen.py](run_unseen.py)).",
        "",
        "## Answer cases (116)",
        "",
        "| Result | Count |",
        "|---|---:|",
        f"| Answered with support | {pct(a['correct_evidence_supported'], n)} |",
        f"| Wrongly refused (evidence exists) | {pct(a['incorrect_refusal_evidence_exists'], n)} |",
        f"| Unsupported answer | {pct(a['unsupported_incorrect_or_misleading'], n)} |",
        f"| Refused, no relevant evidence retrieved (counted as correct refusal by the classifier) | {pct(a['correct_insufficient_information'], n)} |",
        f"| Runtime errors | {a['runtime_error']} |",
        f"| An expected source among the retrieved passages | {pct(a['expected_source_retrieved'], n)} |",
        f"| Mean time per question | {a['mean_seconds']} s |",
        "",
        "## Insufficient cases (4)",
        "",
        f"Correctly refused: {result['insufficient_cases']['correct_insufficient_information']} of {result['insufficient_cases']['n']}; "
        f"answered: {result['insufficient_cases']['unsupported_incorrect_or_misleading']}. Mean time {result['insufficient_cases']['mean_seconds']} s.",
        "",
        "## By topic area (answer cases)",
        "",
        "| Topic area | n | Supported | Wrongly refused | Unsupported | Refused, no evidence | Expected source retrieved | Mean s |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for topic, s in result["by_topic_answer_cases"].items():
        lines.append(
            f"| {topic} | {s['n']} | {s['correct_evidence_supported']} | {s['incorrect_refusal_evidence_exists']} | {s['unsupported_incorrect_or_misleading']} | "
            f"{s['correct_insufficient_information']} | {s['expected_source_retrieved']} | {s['mean_seconds']} |"
        )
    gates = Counter(item["gate"].split(":")[0] for item in result["wrongly_refused"])
    lines += ["", f"## Wrongly refused questions ({len(result['wrongly_refused'])})", "", "By gate: " + ", ".join(f"{gate} {count}" for gate, count in gates.most_common()) + ".", ""]
    lines += ["| Case | Topic | Question | Gate that refused | Expected source retrieved |", "|---|---|---|---|---|"]
    for item in result["wrongly_refused"]:
        lines.append(f"| {item['id']} | {item['topic']} | {item['question']} | {item['gate']} | {'yes' if item['expected_source_retrieved'] else 'no'} |")
    (OUTPUT_DIR / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    for name in ("results.json", "summary.json", "report.md"):
        shutil.copy2(OUTPUT_DIR / name, HERE / name)
    print("\n".join(lines))


STEPS = {"run": step_run, "report": step_report}

if __name__ == "__main__":
    for name in sys.argv[1:]:
        print(f"== {name}", flush=True)
        STEPS[name]()
