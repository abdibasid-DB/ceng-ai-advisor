"""Resumable final-state local Ollama check with representative cases."""

import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
runner = HERE.parent / "reliability-24-live-20261017" / "run_24.py"
spec = importlib.util.spec_from_file_location("reliability_case_runner", runner)
if spec is None or spec.loader is None:
    raise RuntimeError("Cannot load the representative-case runner")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.IDS = (
    "F001", "C019", "C020", "M032", "P056", "H063", "A075", "Y090",
    "R108", "R120", "S129", "X141", "T184", "T187", "T188", "T189",
    "U153", "O166", "N002", "N003", "N004", "N005",
)
module.selected = [module.case_by_id[case_id] for case_id in module.IDS]
module.RESULTS = HERE / "results.json"

if __name__ == "__main__":
    module.main()
