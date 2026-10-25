"""Final evaluation of the frozen system (2026-10-25).

Same steps as docs/final-evaluation-20261023/run_final.py, after the spec-question
fixes (208e21d), temperature 0.2 with seed 42, the prompt-cache reset and the
knowledge-base update (BLS table rows with headers, src_122 club list, src_132
TUIK note). The Ollama server must run with LLAMA_ARG_CACHE_RAM=0.

Steps (each resumable; results go to the evaluation data directory and are copied here):

  full200   official 200-question runner (same dataset, session handling and
            classifier as docs/full-200-evaluation-20261018-reliability), with
            follow-up rewriting applied as in the chat endpoints; answers,
            discarded generations and cited passages are saved
  ceng60    the 60 original ceng-questions.pdf questions with
            scripts/evaluate_rag_quality.py
  spec4     the four specification questions, single turn, through the same
            backend path as full200
  compare   category comparison with the 2026-10-18 and 2026-10-23 runs, incl. mean
            answer time; all runs are labelled again with the current official
            classifier (it calls the pipeline's topic check, which 208e21d changed),
            and the labels recorded at run time are compared too
  nli       NLI faithfulness (scripts/evaluate_nli_claims.py) for all answered cases;
            evaluation only, the pipeline does not use it

Usage: python docs/final-evaluation-20261025/run_final.py STEP [STEP ...]
"""

from __future__ import annotations

import importlib.util
import json
import random
import shutil
import statistics
import subprocess
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from backend.app.api.chat import apply_follow_up_rewrite  # noqa: E402
from backend.app.core.storage_config import ensure_disk_space, prepare_evaluation_storage  # noqa: E402

OUTPUT_DIR = prepare_evaluation_storage("final-evaluation-20261025")
OCT18_RESULTS = OUTPUT_DIR.parent / "full-200-20261018-reliability" / "results.json"
OCT23_DIR = ROOT / "docs" / "final-evaluation-20261023"
RUNNER_PATH = ROOT / "docs" / "full-200-ceng-ai-advisor-evaluation-after-kb-ollama-20261013-202801" / "run_full_200_evaluation.py"
SPEC_QUESTIONS = [
    ("SPEC1", "Will AI replace computer engineers?"),
    ("SPEC2", "Is Computer Engineering still worth studying?"),
    ("SPEC3", "Can I find a job after graduation?"),
    ("SPEC4", "I'm not very good at mathematics. Can I still succeed in Computer Engineering?"),
]
LABELS = [
    "correct_evidence_supported",
    "correct_insufficient_information",
    "incorrect_refusal_evidence_exists",
    "unsupported_incorrect_or_misleading",
    "runtime_error",
]
NLI_THRESHOLD = 0.5


def load_runner():
    spec = importlib.util.spec_from_file_location("official_full_200_runner", RUNNER_PATH)
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    original_run = runner.run_backend_question
    original_resolve = runner.resolve_query

    def run_backend_question(pipeline, question, previous_turn):
        def resolve(question_text, turn):
            return apply_follow_up_rewrite(original_resolve(question_text, turn), [turn] if turn else [], pipeline.llm_service)

        runner.resolve_query = resolve
        try:
            return original_run(pipeline, question, previous_turn)
        finally:
            runner.resolve_query = original_resolve

    runner.run_backend_question = run_backend_question
    return runner


def copy_here(*names: str) -> None:
    for name in names:
        shutil.copy2(OUTPUT_DIR / name, HERE / name)


def step_full200() -> None:
    runner = load_runner()
    runner.RESULTS_PATH = OUTPUT_DIR / "full200-results.json"
    runner.REPORT_PATH = OUTPUT_DIR / "full200-report.md"
    original_write = runner.write_output

    def write_output(results, complete, blocker=None):
        original_write(results, complete, blocker)
        ensure_disk_space()

    runner.write_output = write_output
    sys.argv = [sys.argv[0]]
    runner.main()
    copy_here("full200-results.json", "full200-report.md")


def step_ceng60() -> None:
    cases = json.loads((ROOT / "tests" / "rag_comprehensive_evaluation_cases.json").read_text(encoding="utf-8"))["cases"]
    ids = [case["id"] for case in cases if case["case_kind"] == "original"]
    output, report = OUTPUT_DIR / "ceng60-results.json", OUTPUT_DIR / "ceng60-report.md"
    started = time.perf_counter()
    subprocess.run(
        [sys.executable, "-I", str(ROOT / "scripts" / "evaluate_rag_quality.py"), "--ids", *ids, "--output", str(output), "--report", str(report)],
        check=True,
        cwd=ROOT,
    )
    print(f"ceng60: {len(ids)} questions in {time.perf_counter() - started:.0f} s")
    copy_here("ceng60-results.json", "ceng60-report.md")


def step_spec4() -> None:
    runner = load_runner()
    pipeline = runner.RAGPipeline()
    rows = []
    for case_id, question in SPEC_QUESTIONS:
        started = time.perf_counter()
        result, resolution = runner.run_backend_question(pipeline, question, None)
        rows.append(
            {
                "id": case_id,
                "question": question,
                "status": result.get("status"),
                "answer": result.get("answer"),
                "sources": result.get("sources") or [],
                "retrieved_context": runner.compact_context(result.get("retrieved_context") or []),
                "answer_warnings": result.get("answer_warnings") or [],
                "retrieval_metadata": result.get("retrieval_metadata") or {},
                "citation_metadata": result.get("citation_metadata") or {},
                "elapsed_wall_seconds": round(time.perf_counter() - started, 2),
            }
        )
        print(f"{case_id} {rows[-1]['status']} {rows[-1]['elapsed_wall_seconds']} s", flush=True)
    (OUTPUT_DIR / "spec4-results.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    lines = ["# Specification questions", ""]
    for row in rows:
        lines += [f"## {row['id']}: {row['question']}", "", f"Status: `{row['status']}` · {row['elapsed_wall_seconds']} s", "", row["answer"] or "", ""]
        for item in row["retrieved_context"]:
            lines.append(f"- [{item['label']}] {item['title']} ({item['source_id']}) {item['url']}")
        lines.append("")
    (OUTPUT_DIR / "spec4-report.md").write_text("\n".join(lines), encoding="utf-8")
    copy_here("spec4-results.json", "spec4-report.md")


def by_group(results: list[dict]) -> dict[str, dict]:
    groups: dict[str, list[dict]] = defaultdict(list)
    for row in results:
        groups[row["group"]].append(row)
        groups["ALL"].append(row)
    summary = {}
    for group, rows in groups.items():
        labels = Counter(row["evaluation_label"] for row in rows)
        times = [row["elapsed_wall_seconds"] for row in rows if row.get("elapsed_wall_seconds") is not None]
        summary[group] = {"n": len(rows), **{label: labels.get(label, 0) for label in LABELS}, "mean_seconds": round(statistics.mean(times), 1) if times else None}
    return summary


class Resolution:
    def __init__(self, kind, question):
        self.kind, self.resolved_question = kind, question


def relabel(runner, row: dict) -> str:
    """Label a recorded full200 row again with the current official classifier."""
    diagnostics = row["diagnostics"]
    if diagnostics["status"] == "error":
        return "runtime_error"
    result = {
        "status": diagnostics["status"],
        "answer": row.get("answer"),
        "retrieved_context": row.get("retrieved_context") or [],
        "retrieval_metadata": diagnostics.get("retrieval_metadata") or {},
        "citation_metadata": diagnostics.get("citation_metadata") or {},
    }
    return runner.classify_case(row, result, Resolution(diagnostics.get("query_kind"), diagnostics.get("resolved_question")))[0]


def load_full200(path: Path, runner, relabelled: bool) -> list[dict]:
    rows = json.loads(path.read_text(encoding="utf-8"))["results"]
    if relabelled:
        rows = [{**row, "recorded_label": row["evaluation_label"], "evaluation_label": relabel(runner, row)} for row in rows]
    return rows


def comparison_table(title: str, runs: list[tuple[str, dict]]) -> list[str]:
    lines = [
        f"### {title}",
        "",
        f"Each cell: {' / '.join(name for name, _ in runs)}.",
        "",
        "| Category | n | Supported | Correct refusal | Incorrect refusal | Unsupported | Error | Mean s/answer |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for group in sorted({group for _, summary in runs for group in summary}, key=lambda g: (g == "ALL", g)):
        def cell(key: str) -> str:
            return " / ".join(str(summary.get(group, {}).get(key, "–")) for _, summary in runs)

        name = "**All**" if group == "ALL" else group
        lines.append(
            f"| {name} | {cell('n')} | {cell('correct_evidence_supported')} | {cell('correct_insufficient_information')} | "
            f"{cell('incorrect_refusal_evidence_exists')} | {cell('unsupported_incorrect_or_misleading')} | {cell('runtime_error')} | {cell('mean_seconds')} |"
        )
    return lines + [""]


def ceng60_summary(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    summary = data["summary"]
    times = [case["timing"]["total_seconds"] for case in data["cases"] if case.get("timing", {}).get("total_seconds") is not None]
    return {
        "answer_status_counts": summary["answer_status_counts"],
        "answer_quality_counts": summary["answer_quality_counts"],
        "retrieval_label_counts": summary["retrieval_label_counts"],
        "answered_cases_with_valid_citations": summary["answered_cases_with_valid_citations"],
        "mean_seconds": round(statistics.mean(times), 1) if times else None,
    }


def step_compare() -> None:
    runner = load_runner()
    runs_paths = [("Oct 18", OCT18_RESULTS), ("Oct 23", OCT23_DIR / "full200-results.json"), ("Oct 25", OUTPUT_DIR / "full200-results.json")]
    relabelled = [(name, load_full200(path, runner, True)) for name, path in runs_paths]
    recorded = [(name, load_full200(path, runner, False)) for name, path in runs_paths]
    oct18_ids = {row["id"] for row in relabelled[0][1]}
    spec_runs = (("Oct 23", OCT23_DIR / "spec4-results.json"), ("Oct 25", OUTPUT_DIR / "spec4-results.json"))
    comparison = {
        "relabelled": {name: by_group(rows) for name, rows in relabelled},
        "relabelled_on_oct18_case_ids": {name: by_group([row for row in rows if row["id"] in oct18_ids]) for name, rows in relabelled},
        "recorded": {name: by_group(rows) for name, rows in recorded},
        "ceng60": {"Oct 23": ceng60_summary(OCT23_DIR / "ceng60-results.json"), "Oct 25": ceng60_summary(OUTPUT_DIR / "ceng60-results.json")},
        "spec4": {name: {row["id"]: row["status"] for row in json.loads(path.read_text(encoding="utf-8"))} for name, path in spec_runs},
    }
    old_by_id = {row["id"]: row for row in relabelled[1][1]}
    changes = [
        {"id": row["id"], "group": row["group"], "oct23": old_by_id[row["id"]]["evaluation_label"], "oct25": row["evaluation_label"]}
        for row in sorted(relabelled[2][1], key=lambda item: item["id"])
        if row["id"] in old_by_id and old_by_id[row["id"]]["evaluation_label"] != row["evaluation_label"]
    ]
    comparison["changes_oct23_to_oct25"] = changes
    (OUTPUT_DIR / "comparison.json").write_text(json.dumps(comparison, indent=1, ensure_ascii=False), encoding="utf-8")

    ceng60 = comparison["ceng60"]
    lines = [
        "# Final evaluation (2026-10-25) vs 2026-10-18 and 2026-10-23",
        "",
        f"The 2026-10-18 run is incomplete ({len(oct18_ids)} of 200 cases). The first two tables label all three runs again with the "
        "current official classifier, because it calls the pipeline's topic check, which the spec fix (208e21d) changed; "
        "the third table uses the labels recorded at run time.",
        "",
        "Mean s/answer is `elapsed_wall_seconds` per case; for multi-turn cases it includes the setup turn.",
        "",
    ]
    lines += comparison_table("All cases (current classifier)", [(name, comparison["relabelled"][name]) for name, _ in runs_paths])
    lines += comparison_table("Same case IDs as 2026-10-18 (current classifier)", [(name, comparison["relabelled_on_oct18_case_ids"][name]) for name, _ in runs_paths])
    lines += comparison_table("All cases (labels recorded at run time)", [(name, comparison["recorded"][name]) for name, _ in runs_paths])
    lines += ["### 60 ceng-questions (scripts/evaluate_rag_quality.py)", "", "| | Oct 23 | Oct 25 |", "|---|---:|---:|"]
    for key in ("answer_status_counts", "answer_quality_counts", "retrieval_label_counts"):
        for label in sorted(set(ceng60["Oct 23"][key]) | set(ceng60["Oct 25"][key])):
            lines.append(f"| {label} | {ceng60['Oct 23'][key].get(label, 0)} | {ceng60['Oct 25'][key].get(label, 0)} |")
    lines.append(f"| answered with valid citations | {ceng60['Oct 23']['answered_cases_with_valid_citations']} | {ceng60['Oct 25']['answered_cases_with_valid_citations']} |")
    lines.append(f"| mean s/answer | {ceng60['Oct 23']['mean_seconds']} | {ceng60['Oct 25']['mean_seconds']} |")
    lines += ["", "### Specification questions", "", "| Case | Oct 23 | Oct 25 |", "|---|---|---|"]
    for case_id, _ in SPEC_QUESTIONS:
        lines.append(f"| {case_id} | {comparison['spec4']['Oct 23'].get(case_id)} | {comparison['spec4']['Oct 25'].get(case_id)} |")
    lines += ["", f"### Label changes Oct 23 → Oct 25 (current classifier): {len(changes)}", "", "| Case | Group | Oct 23 | Oct 25 |", "|---|---|---|---|"]
    lines += [f"| {item['id']} | {item['group']} | {item['oct23']} | {item['oct25']} |" for item in changes]
    (OUTPUT_DIR / "comparison.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    copy_here("comparison.json", "comparison.md")
    print("\n".join(lines))


def nli_input() -> Path:
    """All answered cases (full200, ceng60, spec4) in the results format scripts/evaluate_nli_claims.py reads."""
    cases = []
    for row in json.loads((OUTPUT_DIR / "full200-results.json").read_text(encoding="utf-8"))["results"]:
        cases.append({"id": f"full200:{row['id']}", "question": row["question"], "answer": row.get("answer"), "retrieved_context": row.get("retrieved_context") or [], "diagnostics": {"status": row["diagnostics"]["status"]}})
    for row in json.loads((OUTPUT_DIR / "ceng60-results.json").read_text(encoding="utf-8"))["cases"]:
        context = [{"label": item.get("label"), "passage": item.get("passage_preview") or ""} for item in row["retrieval"]["retrieved_passages"]]
        generation = row["generation"]
        cases.append({"id": f"ceng60:{row['id']}", "question": row["question"], "answer": generation.get("answer"), "retrieved_context": context, "diagnostics": {"status": generation.get("status")}})
    for row in json.loads((OUTPUT_DIR / "spec4-results.json").read_text(encoding="utf-8")):
        cases.append({"id": f"spec4:{row['id']}", "question": row["question"], "answer": row.get("answer"), "retrieved_context": row["retrieved_context"], "diagnostics": {"status": row["status"]}})
    path = OUTPUT_DIR / "nli-input.json"
    path.write_text(json.dumps({"results": cases}, ensure_ascii=False, indent=1), encoding="utf-8")
    return path


def step_nli() -> None:
    output = OUTPUT_DIR / "nli-rows.json"
    subprocess.run(
        [sys.executable, "-I", str(ROOT / "scripts" / "evaluate_nli_claims.py"), str(nli_input()), "--thresholds", "0.3", str(NLI_THRESHOLD), "0.7", "--examples", "0", "--output", str(output)],
        check=True,
        cwd=ROOT,
    )
    rows = json.loads(output.read_text(encoding="utf-8"))["rows"]
    scored = [row for row in rows if row["score"] is not None]
    per_case: dict[str, list[float]] = defaultdict(list)
    for row in scored:
        per_case[row["id"]].append(row["score"])

    def summary(prefix: str) -> dict:
        case_scores = {case: scores for case, scores in per_case.items() if case.startswith(prefix)}
        sentence_scores = [score for scores in case_scores.values() for score in scores]
        if not sentence_scores:
            return {"answered_cases_with_cited_sentences": 0}
        return {
            "answered_cases_with_cited_sentences": len(case_scores),
            "cited_sentences": len(sentence_scores),
            "mean_entailment": round(statistics.mean(sentence_scores), 3),
            "sentences_entailed_share": round(sum(score >= NLI_THRESHOLD for score in sentence_scores) / len(sentence_scores), 3),
            "answers_fully_entailed_share": round(sum(all(score >= NLI_THRESHOLD for score in scores) for scores in case_scores.values()) / len(case_scores), 3),
            "mean_answer_faithfulness": round(statistics.mean(sum(score >= NLI_THRESHOLD for score in scores) / len(scores) for scores in case_scores.values()), 3),
        }

    result = {
        "model": "cross-encoder/nli-deberta-v3-small (scripts/evaluate_nli_claims.py defaults: premises=pairs, context=hypothesis)",
        "threshold": NLI_THRESHOLD,
        "all": summary(""),
        "full200": summary("full200:"),
        "ceng60": summary("ceng60:"),
        "spec4": summary("spec4:"),
        "uncited_sentences": sum(1 for row in rows if row.get("note") == "no citation"),
    }
    (OUTPUT_DIR / "nli-faithfulness.json").write_text(json.dumps(result, indent=1), encoding="utf-8")
    copy_here("nli-faithfulness.json", "nli-rows.json")
    print(json.dumps(result, indent=1))


STEPS = {"full200": step_full200, "ceng60": step_ceng60, "spec4": step_spec4, "compare": step_compare, "nli": step_nli}

if __name__ == "__main__":
    for name in sys.argv[1:]:
        print(f"== {name}", flush=True)
        STEPS[name]()
