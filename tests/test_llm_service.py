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

    def __iter__(self):
        if isinstance(self.payload, list):
            for item in self.payload:
                yield (json.dumps(item) + "\n").encode("utf-8")
            return
        yield (json.dumps(self.payload) + "\n").encode("utf-8")


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
    def test_model_availability_is_cached_for_retries(self, mock_urlopen):
        mock_urlopen.return_value = FakeHTTPResponse({"models": [{"name": "qwen2.5:3b"}]})
        service = LocalLLMService()
        self.assertTrue(service.model_available())
        self.assertTrue(service.model_available())
        self.assertEqual(mock_urlopen.call_count, 1)

    @patch("backend.app.services.llm_service.urllib.request.urlopen")
    def test_generate_parses_response(self, mock_urlopen):
        mock_urlopen.side_effect = [
            FakeHTTPResponse({"models": [{"name": "qwen2.5:3b"}]}),
            FakeHTTPResponse(
                {
                    "model": "qwen2.5:3b",
                    "response": "READY",
                    "done": True,
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
    def test_generate_uses_local_streaming_protocol_internally(self, mock_urlopen):
        mock_urlopen.side_effect = [
            FakeHTTPResponse({"models": [{"name": "qwen2.5:3b"}]}),
            FakeHTTPResponse([
                {"model": "qwen2.5:3b", "response": "grounded ", "done": False},
                {"model": "qwen2.5:3b", "response": "answer", "done": True},
            ]),
        ]
        response = LocalLLMService().generate("Answer from evidence")
        self.assertEqual(response.text, "grounded answer")
        payload = json.loads(mock_urlopen.call_args_list[-1].args[0].data)
        self.assertTrue(payload["stream"])

    @patch("backend.app.services.llm_service.urllib.request.urlopen")
    def test_generation_deadline_applies_between_chunks(self, mock_urlopen):
        import time

        from backend.app.services.llm_service import OllamaTimeoutError

        class SlowResponse(FakeHTTPResponse):
            def __iter__(self):
                yield b'{"response":"partial","done":false}\n'
                time.sleep(0.03)
                yield b'{"response":"more","done":true}\n'

        mock_urlopen.side_effect = [
            FakeHTTPResponse({"models": [{"name": "qwen2.5:3b"}]}),
            SlowResponse({}),
        ]
        with self.assertRaises(OllamaTimeoutError):
            LocalLLMService(timeout_seconds=0.01).generate("Answer")

    @patch("backend.app.services.llm_service.urllib.request.urlopen")
    def test_generate_stream_parses_incremental_chunks(self, mock_urlopen):
        mock_urlopen.side_effect = [
            FakeHTTPResponse({"models": [{"name": "qwen2.5:3b"}]}),
            FakeHTTPResponse(
                [
                    {"model": "qwen2.5:3b", "response": "Hello", "done": False},
                    {"model": "qwen2.5:3b", "response": " world", "done": False},
                    {"model": "qwen2.5:3b", "response": "", "done": True, "total_duration": 2_000_000_000},
                ]
            ),
        ]
        chunks = list(LocalLLMService().generate_stream("Say hello"))
        self.assertEqual([chunk.text for chunk in chunks], ["Hello", " world", ""])
        self.assertFalse(chunks[0].done)
        self.assertTrue(chunks[-1].done)
        self.assertEqual(chunks[-1].total_duration_seconds, 2.0)

    @patch("backend.app.services.llm_service.urllib.request.urlopen")
    def test_stream_error_line_raises_local_llm_error(self, mock_urlopen):
        from backend.app.services.llm_service import LocalLLMError

        mock_urlopen.side_effect = [
            FakeHTTPResponse({"models": [{"name": "qwen2.5:3b"}]}),
            FakeHTTPResponse([{"error": "llama runner process has terminated"}]),
        ]
        with self.assertRaises(LocalLLMError):
            LocalLLMService().generate("Answer")

    @patch("backend.app.services.llm_service.urllib.request.urlopen")
    def test_malformed_stream_line_raises_local_llm_error(self, mock_urlopen):
        from backend.app.services.llm_service import LocalLLMError

        class BrokenResponse(FakeHTTPResponse):
            def __iter__(self):
                yield b"not json\n"

        mock_urlopen.side_effect = [
            FakeHTTPResponse({"models": [{"name": "qwen2.5:3b"}]}),
            BrokenResponse({}),
        ]
        with self.assertRaises(LocalLLMError):
            LocalLLMService().generate("Answer")

    @patch("backend.app.services.llm_service.urllib.request.urlopen")
    def test_incomplete_stream_without_done_marker_raises(self, mock_urlopen):
        from backend.app.services.llm_service import LocalLLMError

        mock_urlopen.side_effect = [
            FakeHTTPResponse({"models": [{"name": "qwen2.5:3b"}]}),
            FakeHTTPResponse([{"response": "partial", "done": False}]),
        ]
        with self.assertRaises(LocalLLMError):
            LocalLLMService().generate("Answer")

    def test_stalled_real_stream_respects_total_deadline(self):
        """A server that stops sending mid-stream must not hold the request past the deadline."""
        import threading
        import time
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

        from backend.app.services.llm_service import OllamaTimeoutError

        release = threading.Event()

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                body = json.dumps({"models": [{"name": "qwen2.5:3b"}]}).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_POST(self):
                self.rfile.read(int(self.headers.get("Content-Length", 0)))
                self.send_response(200)
                self.send_header("Content-Type", "application/x-ndjson")
                self.end_headers()
                # Trickle chunks so each individual read is shorter than the
                # timeout, while the whole generation exceeds it.
                for _ in range(20):
                    self.wfile.write(b'{"response":"x","done":false}\n')
                    self.wfile.flush()
                    if release.wait(0.4):
                        return

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            service = LocalLLMService(base_url=f"http://127.0.0.1:{server.server_address[1]}", timeout_seconds=1)
            start = time.monotonic()
            with self.assertRaises(OllamaTimeoutError):
                service.generate("Answer")
            self.assertLess(time.monotonic() - start, 1.8)
        finally:
            release.set()
            server.shutdown()
            server.server_close()

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

    def test_empty_stream_prompt_rejected(self):
        with self.assertRaises(ValueError):
            list(LocalLLMService().generate_stream("   "))


if __name__ == "__main__":
    unittest.main()
