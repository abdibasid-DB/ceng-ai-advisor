import json
import sys
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import Mock, patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.core import llm_config
from backend.app.services.llm_service import (
    LocalLLMService,
    OllamaConnectionError,
    OllamaModelNotFoundError,
)


class FakeHTTPResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


class LLMServiceTests(unittest.TestCase):
    def test_config_uses_local_ollama_without_api_key(self):
        self.assertEqual(llm_config.OLLAMA_BASE_URL, "http://127.0.0.1:11434")
        self.assertEqual(llm_config.SELECTED_LLM_MODEL, "qwen2.5:3b")
        self.assertGreater(llm_config.LLM_REQUEST_TIMEOUT_SECONDS, 0)

    @patch("backend.app.services.llm_service.urllib.request.urlopen")
    def test_model_available(self, mock_urlopen):
        mock_urlopen.return_value = FakeHTTPResponse({"models": [{"name": "qwen2.5:3b"}]})
        self.assertTrue(LocalLLMService().model_available())

    @patch("backend.app.services.llm_service.urllib.request.urlopen")
    def test_generate_parses_response(self, mock_urlopen):
        mock_urlopen.side_effect = [
            FakeHTTPResponse({"models": [{"name": "qwen2.5:3b"}]}),
            FakeHTTPResponse(
                {
                    "model": "qwen2.5:3b",
                    "response": "READY",
                    "total_duration": 1_500_000_000,
                    "load_duration": 100_000_000,
                    "prompt_eval_count": 4,
                    "eval_count": 1,
                    "eval_duration": 200_000_000,
                }
            ),
        ]
        response = LocalLLMService().generate("Respond READY")
        self.assertEqual(response.text, "READY")
        self.assertEqual(response.total_duration_seconds, 1.5)
        self.assertEqual(response.eval_count, 1)

    @patch("backend.app.services.llm_service.urllib.request.urlopen")
    def test_missing_model_error(self, mock_urlopen):
        mock_urlopen.return_value = FakeHTTPResponse({"models": []})
        with self.assertRaises(OllamaModelNotFoundError):
            LocalLLMService().generate("Hello")

    @patch("backend.app.services.llm_service.urllib.request.urlopen")
    def test_connection_error(self, mock_urlopen):
        mock_urlopen.side_effect = urllib.error.URLError("connection refused")
        with self.assertRaises(OllamaConnectionError):
            LocalLLMService().version()

    def test_empty_prompt_rejected(self):
        with self.assertRaises(ValueError):
            LocalLLMService().generate("   ")


if __name__ == "__main__":
    unittest.main()
