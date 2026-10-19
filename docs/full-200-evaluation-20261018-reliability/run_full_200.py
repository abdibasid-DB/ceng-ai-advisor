"""Full 200-question evaluation after the 2026-10-17/18 reliability fixes.

Reuses the previous official runner unchanged (same dataset, same session and
follow-up handling, same automated classifier), so the scores are directly
comparable with docs/full-200-ceng-ai-advisor-evaluation-after-kb-ollama-20261013-202801.
Only storage differs: results, temp files and the Chroma index copy live on
the data drive (backend/app/core/storage_config.py), the run stops if C: runs
low, and the finished results and report are copied into this folder.

Usage: python docs/full-200-evaluation-20261018-reliability/run_full_200.py [--no-resume]
"""

from __future__ import annotations

import importlib.util
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
from backend.app.rag.rag_pipeline import RAGPipeline  # noqa: E402
from backend.app.rag.retriever import Retriever  # noqa: E402

BASELINE_DIR = ROOT / "docs" / "full-200-ceng-ai-advisor-evaluation-after-kb-ollama-20261013-202801"
OUTPUT_DIR = prepare_evaluation_storage("full-200-20261018-reliability")

spec = importlib.util.spec_from_file_location("official_full_200_runner", BASELINE_DIR / "run_full_200_evaluation.py")
if spec is None or spec.loader is None:
    raise RuntimeError("Cannot load the official 200-question runner")
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)

runner.RESULTS_PATH = OUTPUT_DIR / "results.json"
runner.REPORT_PATH = OUTPUT_DIR / "report.md"
runner.RAGPipeline = lambda: RAGPipeline(retriever=Retriever(chroma_path=evaluation_chroma_path()))

_write_output = runner.write_output


def write_output_with_disk_guard(results, complete, blocker=None):
    _write_output(results, complete, blocker)
    ensure_disk_space()


runner.write_output = write_output_with_disk_guard

if __name__ == "__main__":
    runner.main()
    for name in ("results.json", "report.md"):
        shutil.copy2(OUTPUT_DIR / name, HERE / name)
    print(f"copied results to {HERE}", flush=True)
