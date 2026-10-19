"""One-case live verification of the evidence-bounded shell answer."""

from __future__ import annotations

import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("grounding_30_runner", HERE.parent / "grounding-30-final-20261016-180507" / "run_30.py")
if spec is None or spec.loader is None:
    raise RuntimeError("Could not load 30-case runner")
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
case = next(row for row in runner.cases() if row["id"] == "P056")
runner.cases = lambda: [case]
runner.RESULTS = HERE / "p056-recheck.json"

if __name__ == "__main__":
    runner.main()
