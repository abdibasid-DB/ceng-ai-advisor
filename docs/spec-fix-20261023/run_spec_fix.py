"""Before/after runs for the spec-question fixes (2026-10-23).

Runs, through the same backend path as docs/final-evaluation-20261023/run_final.py
(query understanding, LLM follow-up rewrite, official full-200 classifier):

  cases       the 200-question cases of the given groups (--groups) or ids (--ids)
  paraphrase  the 20 paraphrased/unseen cases of tests/rag_comprehensive_evaluation_cases.json,
              labelled with the same classifier (expected categories mapped as in
              scripts/evaluate_rag_quality.py)
  spec4       the four specification questions, single turn

--code-root selects the code and knowledge base that are imported, so the same
script measures an exported copy of the previous commit ("before") and the
working tree ("after"). Results go to the evaluation data directory.

Usage: python docs/spec-fix-20261023/run_spec_fix.py STEP [--code-root DIR] [--name NAME] [--groups g1,g2] [--ids id1,id2]
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

SPEC_QUESTIONS = [
    ("SPEC1", "Will AI replace computer engineers?"),
    ("SPEC2", "Is Computer Engineering still worth studying?"),
    ("SPEC3", "Can I find a job after graduation?"),
    ("SPEC4", "I'm not very good at mathematics. Can I still succeed in Computer Engineering?"),
]
RUNNER = "docs/full-200-ceng-ai-advisor-evaluation-after-kb-ollama-20261013-202801/run_full_200_evaluation.py"


def load_runner(code_root: Path):
    sys.path.insert(0, str(code_root))
    from backend.app.api.chat import apply_follow_up_rewrite

    spec = importlib.util.spec_from_file_location("official_full_200_runner", code_root / RUNNER)
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    original_resolve = runner.resolve_query
    original_run = runner.run_backend_question

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


def run_case(runner, pipeline, case: dict) -> dict:
    started = time.perf_counter()
    previous_result = previous_turn = None
    if case.get("previous_question"):
        previous_result, _ = runner.run_backend_question(pipeline, case["previous_question"], None)
        previous_turn = runner.previous_turn_from_result(case["previous_question"], previous_result)
    result, resolution = runner.run_backend_question(pipeline, case["question"], previous_turn)
    label, diagnostics = runner.classify_case(case, result, resolution)
    return {
        **case,
        "evaluation_label": label,
        "elapsed_wall_seconds": round(time.perf_counter() - started, 3),
        "diagnostics": diagnostics,
        "answer": result.get("answer"),
        "answer_warnings": result.get("answer_warnings") or [],
        "sources": result.get("sources") or [],
        "retrieved_context": runner.compact_context(result.get("retrieved_context") or []),
        "previous_turn_setup": None
        if not previous_result
        else {"question": case["previous_question"], "status": previous_result.get("status"), "answer": previous_result.get("answer")},
    }


def paraphrase_cases(code_root: Path) -> list[dict]:
    spec = importlib.util.spec_from_file_location("evaluate_rag_quality", code_root / "scripts" / "evaluate_rag_quality.py")
    quality = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(quality)
    cases = json.loads((code_root / "tests" / "rag_comprehensive_evaluation_cases.json").read_text(encoding="utf-8"))["cases"]
    converted = []
    for case in cases:
        if case["case_kind"] == "original":
            continue
        categories = list(case["expected_categories"])
        for category in case["expected_categories"]:
            categories += quality.CATEGORY_COMPATIBILITY.get(category, ())
        converted.append({
            "id": case["id"],
            "question": case["question"],
            "group": "paraphrase",
            "expected_topics": [],
            "expected_categories": list(dict.fromkeys(categories)),
            "expected_behavior": "answer_or_gap",
            "previous_question": None,
        })
    return converted


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("step", choices=("cases", "paraphrase", "spec4"))
    parser.add_argument("--code-root", default=str(REPO))
    parser.add_argument("--name", default="after")
    parser.add_argument("--groups", default="")
    parser.add_argument("--ids", default="")
    args = parser.parse_args()
    code_root = Path(args.code_root).resolve()

    sys.path.insert(0, str(REPO))
    from backend.app.core.storage_config import ensure_disk_space, prepare_evaluation_storage

    output_dir = prepare_evaluation_storage("spec-fix-20261023")
    sys.path.remove(str(REPO))
    for name in [module for module in sys.modules if module == "backend" or module.startswith("backend.")]:
        del sys.modules[name]
    runner = load_runner(code_root)
    pipeline = runner.RAGPipeline()

    if args.step == "cases":
        groups = {group for group in args.groups.split(",") if group}
        ids = {case_id for case_id in args.ids.split(",") if case_id}
        cases = [case for case in runner.load_cases() if case["group"] in groups or case["id"] in ids]
    elif args.step == "paraphrase":
        cases = paraphrase_cases(code_root)
    else:
        cases = [{"id": case_id, "question": question, "group": "spec", "expected_topics": [], "expected_categories": [],
                  "expected_behavior": "answer_or_gap", "previous_question": None} for case_id, question in SPEC_QUESTIONS]

    path = output_dir / f"{args.step}-{args.name}.json"
    rows = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    done = {row["id"] for row in rows}
    for number, case in enumerate(cases, start=1):
        if case["id"] in done:
            continue
        rows.append(run_case(runner, pipeline, case))
        path.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"{number}/{len(cases)} {case['id']} {rows[-1]['evaluation_label']} {rows[-1]['elapsed_wall_seconds']} s", flush=True)
        ensure_disk_space()
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
