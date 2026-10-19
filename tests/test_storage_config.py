import importlib
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.core import storage_config


class StorageConfigTests(unittest.TestCase):
    def tearDown(self):
        importlib.reload(storage_config)

    def test_environment_overrides_data_locations(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(os.environ, {"CENG_DATA_DIR": directory}):
                module = importlib.reload(storage_config)
                self.assertEqual(module.EVALUATION_OUTPUT_DIR, Path(directory) / "evaluations")
                self.assertEqual(module.TEMP_DIR, Path(directory) / "tmp")

    def test_low_system_drive_space_stops_evaluation(self):
        with patch.object(storage_config, "free_gb", return_value=0.5):
            with self.assertRaises(storage_config.LowDiskSpaceError):
                storage_config.ensure_disk_space()

    def test_missing_evaluation_index_falls_back_to_project_index(self):
        with patch.object(storage_config, "EVALUATION_CHROMA_PATH", Path("Z:/does-not-exist")):
            self.assertEqual(storage_config.evaluation_chroma_path(), storage_config.CHROMA_PATH)


if __name__ == "__main__":
    unittest.main()
