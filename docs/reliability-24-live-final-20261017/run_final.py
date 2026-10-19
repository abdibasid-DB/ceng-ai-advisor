"""Run the same 24 cases against the final retrieval and retry code state."""

import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
runner = HERE.parent / "reliability-24-live-20261017" / "run_24.py"
spec = importlib.util.spec_from_file_location("reliability_24_runner", runner)
if spec is None or spec.loader is None:
    raise RuntimeError("Cannot load the 24-case runner")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.RESULTS = HERE / "results.json"

if __name__ == "__main__":
    module.main()
