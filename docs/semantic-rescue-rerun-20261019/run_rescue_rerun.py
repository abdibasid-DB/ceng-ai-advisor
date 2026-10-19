"""Re-run the 43 LLM-called incorrect refusals from the 2026-10-18 full-200 run.

Uses the official runner (same session/follow-up handling and classifier) on
only those cases, after the semantic grounding checks were added. The
classifier runs with the semantic encoder disabled so labels use the same
lexical standard as the baseline run. Raw model output for any discarded
answer is stored in diagnostics.retrieval_metadata.discarded_generation.

Usage: python docs/semantic-rescue-rerun-20261019/run_rescue_rerun.py BASELINE_RESULTS_JSON
"""

from __future__ import annotations

import importlib.util
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.core.storage_config import (  # noqa: E402
    ensure_disk_space,
    evaluation_chroma_path,
    prepare_evaluation_storage,
)
from backend.app.rag import rag_pipeline as rp  # noqa: E402
from backend.app.rag.retriever import Retriever  # noqa: E402

BASELINE_RUNNER = ROOT / "docs" / "full-200-ceng-ai-advisor-evaluation-after-kb-ollama-20261013-202801" / "run_full_200_evaluation.py"
OUTPUT_DIR = prepare_evaluation_storage("semantic-rescue-rerun-20261019")

spec = importlib.util.spec_from_file_location("official_full_200_runner", BASELINE_RUNNER)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)

pipeline = rp.RAGPipeline(retriever=Retriever(chroma_path=evaluation_chroma_path()))
runner.RAGPipeline = lambda: pipeline
runner.RESULTS_PATH = OUTPUT_DIR / "results.json"
runner.REPORT_PATH = OUTPUT_DIR / "report.md"

_classify = runner.classify_case


def classify_with_lexical_standard(case, result, resolution):
    encoder = rp._semantic_encoder
    rp.configure_semantic_encoder(None)
    try:
        return _classify(case, result, resolution)
    finally:
        rp.configure_semantic_encoder(encoder)


runner.classify_case = classify_with_lexical_standard

_write_output = runner.write_output


def write_output_with_disk_guard(results, complete, blocker=None):
    _write_output(results, complete, blocker)
    ensure_disk_space()


runner.write_output = write_output_with_disk_guard


def main() -> None:
    baseline = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))["results"]
    target_ids = {
        case["id"] for case in baseline
        if case["evaluation_label"] == "incorrect_refusal_evidence_exists" and case["diagnostics"]["llm_called"]
    }
    print(f"re-running {len(target_ids)} cases", flush=True)
    all_cases = runner.load_cases()
    runner.load_cases = lambda: all_cases
    # The official main() iterates all 200 cases and skips ids already in the
    # results file, so pre-mark every non-target case as done.
    skip = [{"id": case["id"], "_skip": True} for case in all_cases if case["id"] not in target_ids]
    existing = json.loads(runner.RESULTS_PATH.read_text(encoding="utf-8")) if runner.RESULTS_PATH.exists() else {"results": []}
    kept = [row for row in existing.get("results") or [] if not row.get("_skip")]
    runner.RESULTS_PATH.write_text(json.dumps({"results": skip + kept}), encoding="utf-8")

    original_summarize = runner.summarize
    runner.summarize = lambda rows: original_summarize([row for row in rows if not row.get("_skip")])
    original_failures = runner.systematic_failures
    runner.systematic_failures = lambda rows: original_failures([row for row in rows if not row.get("_skip")])
    sys.argv = [sys.argv[0]]
    runner.main()

    final = json.loads(runner.RESULTS_PATH.read_text(encoding="utf-8"))
    rows = [row for row in final["results"] if not row.get("_skip")]
    runner.summarize = original_summarize
    runner.systematic_failures = original_failures
    _write_output(rows, final.get("complete", False), final.get("blocker"))
    for name in ("results.json", "report.md"):
        shutil.copy2(OUTPUT_DIR / name, HERE / name)
    print(f"copied results to {HERE}", flush=True)


if __name__ == "__main__":
    main()
