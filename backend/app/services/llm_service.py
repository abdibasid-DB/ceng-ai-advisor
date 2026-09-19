"""Local Ollama client for Stage 14.

This service only communicates with a locally running Ollama model. It does
not connect retrieval results to the model, construct RAG prompts, create final
advisor answers, or call commercial cloud LLM APIs.
"""

from __future__ import annotations

import json
import socket
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from ..core.llm_config import (
    LLM_NUM_CTX,
    LLM_NUM_PREDICT,
    LLM_KEEP_ALIVE,
    LLM_REQUEST_TIMEOUT_SECONDS,
    LLM_TEMPERATURE,
    OLLAMA_BASE_URL,
    OLLAMA_GENERATE_ENDPOINT,
    OLLAMA_TAGS_ENDPOINT,
    OLLAMA_VERSION_ENDPOINT,
    SELECTED_LLM_MODEL,
)


class LocalLLMError(RuntimeError):
    """Base error for local LLM failures."""


class OllamaConnectionError(LocalLLMError):
    """Raised when the local Ollama service cannot be reached."""


class OllamaModelNotFoundError(LocalLLMError):
    """Raised when the configured model is not available locally."""


class OllamaTimeoutError(LocalLLMError):
    """Raised when local generation times out."""


@dataclass(frozen=True)
class LLMResponse:
    text: str
    model: str
    total_duration_seconds: float
    load_duration_seconds: float | None
    prompt_eval_count: int | None
    eval_count: int | None
    eval_duration_seconds: float | None
    wall_time_seconds: float
    raw: dict[str, Any]


class LocalLLMService:
    def __init__(
        self,
        *,
        base_url: str = OLLAMA_BASE_URL,
        model: str = SELECTED_LLM_MODEL,
        timeout_seconds: int = LLM_REQUEST_TIMEOUT_SECONDS,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds

    def version(self) -> dict[str, Any]:
        return self._request_json("GET", OLLAMA_VERSION_ENDPOINT)

    def list_models(self) -> list[dict[str, Any]]:
        data = self._request_json("GET", OLLAMA_TAGS_ENDPOINT)
        return data.get("models", [])

    def model_available(self) -> bool:
        return any(item.get("name") == self.model or item.get("model") == self.model for item in self.list_models())

    def generate(
        self,
        prompt: str,
        *,
        temperature: float = LLM_TEMPERATURE,
        num_ctx: int = LLM_NUM_CTX,
        num_predict: int = LLM_NUM_PREDICT,
        keep_alive: str | None = LLM_KEEP_ALIVE,
    ) -> LLMResponse:
        cleaned = " ".join((prompt or "").split())
        if not cleaned:
            raise ValueError("Prompt must not be empty.")
        if not self.model_available():
            raise OllamaModelNotFoundError(
                f"Local Ollama model '{self.model}' is not available. Run: ollama pull {self.model}"
            )

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "keep_alive": keep_alive,
            "options": {
                "temperature": temperature,
                "num_ctx": num_ctx,
                "num_predict": num_predict,
            },
        }
        start = time.perf_counter()
        data = self._request_json("POST", OLLAMA_GENERATE_ENDPOINT, payload)
        wall_time = time.perf_counter() - start

        return LLMResponse(
            text=data.get("response", ""),
            model=data.get("model", self.model),
            total_duration_seconds=nanoseconds_to_seconds(data.get("total_duration")),
            load_duration_seconds=optional_nanoseconds_to_seconds(data.get("load_duration")),
            prompt_eval_count=data.get("prompt_eval_count"),
            eval_count=data.get("eval_count"),
            eval_duration_seconds=optional_nanoseconds_to_seconds(data.get("eval_duration")),
            wall_time_seconds=wall_time,
            raw=data,
        )

    def _request_json(self, method: str, endpoint: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        url = f"{self.base_url}{endpoint}"
        data = None
        headers = {"Accept": "application/json"}
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"

        request = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            if exc.code == 404 and "model" in body.lower():
                raise OllamaModelNotFoundError(body) from exc
            raise LocalLLMError(f"Ollama HTTP error {exc.code}: {body}") from exc
        except socket.timeout as exc:
            raise OllamaTimeoutError(f"Ollama request timed out after {self.timeout_seconds} seconds.") from exc
        except urllib.error.URLError as exc:
            raise OllamaConnectionError(f"Could not connect to local Ollama at {self.base_url}: {exc.reason}") from exc


def nanoseconds_to_seconds(value: Any) -> float:
    if value is None:
        return 0.0
    return round(float(value) / 1_000_000_000, 3)


def optional_nanoseconds_to_seconds(value: Any) -> float | None:
    if value is None:
        return None
    return nanoseconds_to_seconds(value)
