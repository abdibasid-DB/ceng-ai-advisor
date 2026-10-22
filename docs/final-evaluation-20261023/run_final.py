"""Final evaluation after retrieval option f, removal of hand-written passages and follow-up rewriting.

Steps (each resumable; results go to the evaluation data directory and are copied here):

  full200   official 200-question runner (same dataset, session handling and
            classifier as docs/full-200-evaluation-20261018-reliability), with
            follow-up rewriting applied as in the chat endpoints; answers,
            discarded generations and cited passages are saved
  ceng60    the 60 original ceng-questions.pdf questions with
            scripts/evaluate_rag_quality.py
  spec4     the four specification questions, single turn, through the same
            backend path as full200
  compare   category comparison with the 2026-10-18 run, incl. mean answer time
  nli       NLI faithfulness (scripts/evaluate_nli_claims.py) for all answered cases
  manual30  docs/manual-check-30.md: 30 random answered cases for manual review

Usage: python docs/final-evaluation-20261023/run_final.py STEP [STEP ...]
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

OUTPUT_DIR = prepare_evaluation_storage("final-evaluation-20261023")
OCT18_RESULTS = OUTPUT_DIR.parent / "full-200-20261018-reliability" / "results.json"
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


def step_compare() -> None:
    new = json.loads((OUTPUT_DIR / "full200-results.json").read_text(encoding="utf-8"))["results"]
    old = json.loads(OCT18_RESULTS.read_text(encoding="utf-8"))["results"]
    old_ids = {row["id"] for row in old}
    new_same = [row for row in new if row["id"] in old_ids]
    comparison = {"oct18": by_group(old), "final": by_group(new), "final_on_oct18_case_ids": by_group(new_same)}
    (OUTPUT_DIR / "comparison.json").write_text(json.dumps(comparison, indent=1), encoding="utf-8")

    def table(title: str, old_summary: dict, new_summary: dict) -> list[str]:
        lines = [f"### {title}", "", "| Category | n (Oct 18 / now) | Supported | Correct refusal | Incorrect refusal | Unsupported | Mean s/answer |", "|---|---:|---:|---:|---:|---:|---:|"]
        for group in sorted(set(old_summary) | set(new_summary), key=lambda g: (g == "ALL", g)):
            o, n = old_summary.get(group, {}), new_summary.get(group, {})

            def cell(key: str) -> str:
                return f"{o.get(key, '–')} → {n.get(key, '–')}"

            name = "**All**" if group == "ALL" else group
            lines.append(
                f"| {name} | {o.get('n', 0)} / {n.get('n', 0)} | {cell('correct_evidence_supported')} | {cell('correct_insufficient_information')} | "
                f"{cell('incorrect_refusal_evidence_exists')} | {cell('unsupported_incorrect_or_misleading')} | {cell('mean_seconds')} |"
            )
        return lines + [""]

    lines = [
        "# Final evaluation vs 2026-10-18",
        "",
        f"The 2026-10-18 run is incomplete ({len(old)} of 200 cases); the second table restricts the new run to the same case IDs.",
        "",
        "Mean s/answer is `elapsed_wall_seconds` per case in both runs; for multi-turn cases it includes the setup turn, "
        "so it is higher than the per-answer latency in full200-report.md.",
        "",
    ]
    lines += table("All cases", comparison["oct18"], comparison["final"])
    lines += table("Same case IDs as 2026-10-18", comparison["oct18"], comparison["final_on_oct18_case_ids"])
    (OUTPUT_DIR / "comparison.md").write_text("\n".join(lines), encoding="utf-8")
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


def step_manual30() -> None:
    answered = []
    for row in json.loads((OUTPUT_DIR / "full200-results.json").read_text(encoding="utf-8"))["results"]:
        if row["diagnostics"]["status"] == "answered":
            answered.append(("full200", row["id"], row["question"], row.get("previous_question"), row["answer"], row.get("retrieved_context") or []))
    for row in json.loads((OUTPUT_DIR / "ceng60-results.json").read_text(encoding="utf-8"))["cases"]:
        if row["generation"].get("status") == "answered":
            answered.append(("ceng60", row["id"], row["question"], None, row["generation"]["answer"], row["retrieval"]["retrieved_passages"]))
    for row in json.loads((OUTPUT_DIR / "spec4-results.json").read_text(encoding="utf-8")):
        if row["status"] == "answered":
            answered.append(("spec4", row["id"], row["question"], None, row["answer"], row["retrieved_context"]))
    sample = sorted(random.Random(20261023).sample(answered, min(30, len(answered))), key=lambda item: (item[0], item[1]))

    lines = [
        "# Manual check: 30 answered cases",
        "",
        f"Random sample (seed 20261023) of {len(sample)} out of {len(answered)} answered cases from the final evaluation "
        "(docs/final-evaluation-20261023/: full200, ceng60 and spec4 results). Each case shows the question, the answer as "
        "the student saw it, and the full text of every passage the model was given, labelled as in the answer's citations.",
        "",
        "For each case fill in the verdict (correct / partly correct / wrong) and a note.",
        "",
    ]
    for number, (run, case_id, question, previous, answer, context) in enumerate(sample, start=1):
        lines += [f"## {number}. {run} {case_id}", ""]
        if previous:
            lines += [f"**Previous question:** {previous}", ""]
        lines += [f"**Question:** {question}", "", "**Answer:**", "", *[f"> {line}" if line else ">" for line in (answer or "").splitlines()], "", "**Cited passages:**", ""]
        for item in context:
            lines += [f"- **[{item.get('label')}]** {item.get('title') or ''} ({item.get('source_id')}) {item.get('url') or ''}", "", f"  > {' '.join((item.get('passage') or item.get('passage_preview') or '').split())}", ""]
        lines += ["**Verdict (correct / partly correct / wrong):** ", "", "**Note:** ", "", "---", ""]
    (ROOT / "docs" / "manual-check-30.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote docs/manual-check-30.md with {len(sample)} cases")


STEPS = {"full200": step_full200, "ceng60": step_ceng60, "spec4": step_spec4, "compare": step_compare, "nli": step_nli, "manual30": step_manual30}

if __name__ == "__main__":
    for name in sys.argv[1:]:
        print(f"== {name}", flush=True)
        STEPS[name]()
