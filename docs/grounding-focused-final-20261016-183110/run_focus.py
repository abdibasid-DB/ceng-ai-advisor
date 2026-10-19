"""Resume-safe live recheck of cases affected by the final grounding guards."""

from __future__ import annotations

import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUNNER = HERE.parent / "grounding-30-final-20261016-180507" / "run_30.py"
SELECTED_IDS = ("F001", "C020", "R120", "X141", "T187", "T188", "N001", "N002", "N003", "Y090", "U153")

spec = importlib.util.spec_from_file_location("grounding_30_runner", RUNNER)
if spec is None or spec.loader is None:
    raise RuntimeError("Could not load 30-case runner")
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
selected = {row["id"]: row for row in runner.cases()}
runner.cases = lambda: [selected[case_id] for case_id in SELECTED_IDS]
runner.RESULTS = HERE / "results.json"

if __name__ == "__main__":
    runner.main()
