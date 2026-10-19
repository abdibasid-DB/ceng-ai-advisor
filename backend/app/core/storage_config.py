"""Where large, regenerable evaluation data is written.

The system drive (C:) on the development machine is small, so evaluation
outputs, temporary files, and the evaluation copy of the Chroma index live on a
data drive. Every location can be overridden with an environment variable, and
everything falls back to the project folder on machines without a D: drive.

The application itself keeps reading the project's knowledge base by default;
only evaluation scripts use these locations.
"""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path

from .retrieval_config import CHROMA_PATH, PROJECT_ROOT


def _default_data_dir() -> Path:
    data_drive = Path("D:/")
    if os.name == "nt" and data_drive.exists():
        return data_drive / "ceng-ai-advisor-data"
    return PROJECT_ROOT / ".local-data"


DATA_DIR = Path(os.environ.get("CENG_DATA_DIR") or _default_data_dir())
EVALUATION_OUTPUT_DIR = Path(os.environ.get("CENG_EVAL_OUTPUT_DIR") or DATA_DIR / "evaluations")
TEMP_DIR = Path(os.environ.get("CENG_TEMP_DIR") or DATA_DIR / "tmp")
# Identical copy of the project index used by evaluations so their Chroma
# reads and SQLite writes do not touch the system drive.
EVALUATION_CHROMA_PATH = Path(os.environ.get("CENG_EVAL_CHROMA_PATH") or DATA_DIR / "chroma")

# Stop long evaluation runs before they push the system drive into a state
# where Windows, Ollama, or Git writes start failing.
MIN_SYSTEM_DRIVE_FREE_GB = float(os.environ.get("CENG_MIN_SYSTEM_FREE_GB") or 3.0)


class LowDiskSpaceError(RuntimeError):
    """Raised when continuing would risk filling a drive."""


def free_gb(path: Path) -> float:
    anchor = Path(path).resolve().anchor or str(path)
    return shutil.disk_usage(anchor).free / 1024**3


def ensure_disk_space(*, system_drive: Path = Path(os.environ.get("SystemDrive", "C:") + "/")) -> None:
    """Raise LowDiskSpaceError if the system drive is below the safety margin."""
    available = free_gb(system_drive)
    if available < MIN_SYSTEM_DRIVE_FREE_GB:
        raise LowDiskSpaceError(
            f"Only {available:.1f} GB free on {system_drive}; evaluation stopped to keep the system drive usable "
            f"(minimum {MIN_SYSTEM_DRIVE_FREE_GB:.1f} GB). Free space or set CENG_MIN_SYSTEM_FREE_GB."
        )


def prepare_evaluation_storage(run_name: str) -> Path:
    """Create the output folder for one evaluation run and route temp files to the data drive."""
    ensure_disk_space()
    output_dir = EVALUATION_OUTPUT_DIR / run_name
    output_dir.mkdir(parents=True, exist_ok=True)
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    for variable in ("TMP", "TEMP", "TMPDIR"):
        os.environ[variable] = str(TEMP_DIR)
    tempfile.tempdir = str(TEMP_DIR)
    return output_dir


def evaluation_chroma_path() -> Path:
    """Use the data-drive index copy when it exists, otherwise the project index."""
    if (EVALUATION_CHROMA_PATH / "chroma.sqlite3").exists():
        return EVALUATION_CHROMA_PATH
    return CHROMA_PATH
