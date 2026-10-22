"""Part 3 check: LLM follow-up rewriting on the multi-turn cases of the 200-question set.

Runs every case that has a previous question (group multi_turn, including
T184 and T189) through the official 200-question runner's backend path and
classifier, once with the follow-up rewrite off and once with it on. The
rewrite is applied exactly as the chat endpoints apply it
(backend.app.api.chat.apply_follow_up_rewrite).

Single-turn cases have no previous turn, so needs_rewrite() is never true for
them; the script counts this explicitly over all single-turn cases.

Usage: python docs/follow-up-rewrite-20261022/run_multi_turn.py off|on
"""

from __future__ import annotations

import importlib.util
import json
import shutil
import sys
import time
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from backend.app.api.chat import apply_follow_up_rewrite  # noqa: E402
from backend.app.core.storage_config import ensure_disk_space, prepare_evaluation_storage  # noqa: E402
from backend.app.query_understanding import resolve_query  # noqa: E402
from backend.app.services.follow_up_rewriter import needs_rewrite  # noqa: E402

RUNNER_PATH = ROOT / "docs" / "full-200-ceng-ai-advisor-evaluation-after-kb-ollama-20261013-202801" / "run_full_200_evaluation.py"
spec = importlib.util.spec_from_file_location("official_full_200_runner", RUNNER_PATH)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


def run_with_rewrite(enabled: bool):
    original_resolve = runner.resolve_query

    def run_backend_question(pipeline, question, previous_turn):
        def resolve(question_text, turn):
            resolution = original_resolve(question_text, turn)
            return apply_follow_up_rewrite(resolution, [turn] if turn else [], pipeline.llm_service, enabled=enabled)

        runner.resolve_query = resolve
        try:
            return ORIGINAL_RUN(pipeline, question, previous_turn)
        finally:
            runner.resolve_query = original_resolve

    return run_backend_question


ORIGINAL_RUN = runner.run_backend_question


def main() -> int:
    mode = sys.argv[1]
    if mode not in {"off", "on"}:
        raise SystemExit("usage: run_multi_turn.py off|on")
    cases = runner.load_cases()
    single_turn = [case for case in cases if not case.get("previous_question")]
    triggered = sum(needs_rewrite(case["question"], resolve_query(case["question"], None).kind, False) for case in single_turn)
    print(f"single-turn cases: {len(single_turn)}; rewrite triggered: {triggered}")
    multi = [case for case in cases if case.get("previous_question")]

    output_dir = prepare_evaluation_storage("follow-up-rewrite-20261022")
    path = output_dir / f"{mode}.json"
    results = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    done = {row["id"] for row in results}
    pipeline = runner.RAGPipeline()
    run = run_with_rewrite(mode == "on")
    for case in multi:
        if case["id"] in done:
            continue
        started = time.perf_counter()
        previous_result, _ = ORIGINAL_RUN(pipeline, case["previous_question"], None)
        previous_turn = runner.previous_turn_from_result(case["previous_question"], previous_result)
        result, resolution = run(pipeline, case["question"], previous_turn)
        label, diagnostics = runner.classify_case(case, result, resolution)
        results.append(
            {
                **case,
                "evaluation_label": label,
                "status": result.get("status"),
                "answer": result.get("answer"),
                "resolved_question": resolution.resolved_question,
                "follow_up_rewrite": (result.get("retrieval_metadata") or {}).get("follow_up_rewrite"),
                "previous_answer": previous_result.get("answer"),
                "sources": [source.get("source_id") for source in result.get("sources") or []],
                "diagnostics": diagnostics,
                "elapsed_wall_seconds": round(time.perf_counter() - started, 2),
            }
        )
        path.write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"{case['id']} {label} {resolution.resolved_question}", flush=True)
        ensure_disk_space()

    print(json.dumps(Counter(row["evaluation_label"] for row in results), indent=1))
    summary = {"mode": mode, "single_turn_cases": len(single_turn), "single_turn_rewrite_triggered": triggered, "labels": Counter(row["evaluation_label"] for row in results)}
    (output_dir / f"{mode}-summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    for name in (f"{mode}.json", f"{mode}-summary.json"):
        shutil.copy2(output_dir / name, HERE / name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
