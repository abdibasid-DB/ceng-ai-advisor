"""Local Ollama client for Stage 14.

This service only communicates with a locally running Ollama model. It does
not connect retrieval results to the model, construct RAG prompts, create final
advisor answers, or call commercial cloud LLM APIs.
"""

from __future__ import annotations

import http.client
import json
import socket
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from collections.abc import Iterator
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


@dataclass(frozen=True)
class LLMStreamChunk:
    text: str
    done: bool
    model: str
    total_duration_seconds: float = 0.0
    load_duration_seconds: float | None = None
    prompt_eval_count: int | None = None
    eval_count: int | None = None
    eval_duration_seconds: float | None = None
    raw: dict[str, Any] | None = None


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
        self._model_available_until = 0.0

    def version(self) -> dict[str, Any]:
        return self._request_json("GET", OLLAMA_VERSION_ENDPOINT)

    def list_models(self) -> list[dict[str, Any]]:
        data = self._request_json("GET", OLLAMA_TAGS_ENDPOINT)
        return data.get("models", [])

    def model_available(self) -> bool:
        if time.monotonic() < self._model_available_until:
            return True
        available = any(item.get("name") == self.model or item.get("model") == self.model for item in self.list_models())
        if available:
            self._model_available_until = time.monotonic() + 60.0
        return available

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
        start = time.perf_counter()
        parts: list[str] = []
        final_chunk: LLMStreamChunk | None = None
        for chunk in self.generate_stream(
            prompt, temperature=temperature, num_ctx=num_ctx,
            num_predict=num_predict, keep_alive=keep_alive,
        ):
            parts.append(chunk.text)
            final_chunk = chunk
        if final_chunk is None or not final_chunk.done:
            raise LocalLLMError("Ollama ended generation without a completion marker.")
        wall_time = time.perf_counter() - start

        return LLMResponse(
            text="".join(parts),
            model=final_chunk.model,
            total_duration_seconds=final_chunk.total_duration_seconds,
            load_duration_seconds=final_chunk.load_duration_seconds,
            prompt_eval_count=final_chunk.prompt_eval_count,
            eval_count=final_chunk.eval_count,
            eval_duration_seconds=final_chunk.eval_duration_seconds,
            wall_time_seconds=wall_time,
            raw=final_chunk.raw or {},
        )

    def generate_stream(
        self,
        prompt: str,
        *,
        temperature: float = LLM_TEMPERATURE,
        num_ctx: int = LLM_NUM_CTX,
        num_predict: int = LLM_NUM_PREDICT,
        keep_alive: str | None = LLM_KEEP_ALIVE,
    ) -> Iterator[LLMStreamChunk]:
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
            "stream": True,
            "keep_alive": keep_alive,
            "options": {
                "temperature": temperature,
                "num_ctx": num_ctx,
                "num_predict": num_predict,
            },
        }
        url = f"{self.base_url}{OLLAMA_GENERATE_ENDPOINT}"
        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=data,
            headers={"Accept": "application/x-ndjson", "Content-Type": "application/json"},
            method="POST",
        )

        deadline = time.monotonic() + self.timeout_seconds
        timeout_message = f"Ollama generation exceeded {self.timeout_seconds} seconds."
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                sock = _response_socket(response)
                lines = iter(response)
                while True:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise OllamaTimeoutError(timeout_message)
                    # Bound each read by the time left so a stalled stream
                    # cannot extend the total generation beyond the deadline.
                    if sock is not None:
                        sock.settimeout(remaining)
                    raw_line = next(lines, None)
                    if raw_line is None:
                        break
                    if time.monotonic() > deadline:
                        raise OllamaTimeoutError(timeout_message)
                    line = raw_line.decode("utf-8", errors="replace").strip()
                    if not line:
                        continue
                    try:
                        item = json.loads(line)
                    except json.JSONDecodeError as exc:
                        raise LocalLLMError(f"Ollama returned malformed stream data: {line[:200]}") from exc
                    if not isinstance(item, dict):
                        raise LocalLLMError(f"Ollama returned unexpected stream data: {line[:200]}")
                    if item.get("error"):
                        error_text = str(item["error"])
                        if "not found" in error_text.lower() and "model" in error_text.lower():
                            self._model_available_until = 0.0
                            raise OllamaModelNotFoundError(error_text)
                        raise LocalLLMError(f"Ollama generation error: {error_text}")
                    yield LLMStreamChunk(
                        text=item.get("response", ""),
                        done=bool(item.get("done")),
                        model=item.get("model", self.model),
                        total_duration_seconds=nanoseconds_to_seconds(item.get("total_duration")),
                        load_duration_seconds=optional_nanoseconds_to_seconds(item.get("load_duration")),
                        prompt_eval_count=item.get("prompt_eval_count"),
                        eval_count=item.get("eval_count"),
                        eval_duration_seconds=optional_nanoseconds_to_seconds(item.get("eval_duration")),
                        raw=item,
                    )
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            if exc.code == 404 and "model" in body.lower():
                self._model_available_until = 0.0
                raise OllamaModelNotFoundError(body) from exc
            raise LocalLLMError(f"Ollama HTTP error {exc.code}: {body}") from exc
        except (socket.timeout, TimeoutError) as exc:
            raise OllamaTimeoutError(timeout_message) from exc
        except urllib.error.URLError as exc:
            if isinstance(exc.reason, (socket.timeout, TimeoutError)):
                raise OllamaTimeoutError(timeout_message) from exc
            raise OllamaConnectionError(f"Could not connect to local Ollama at {self.base_url}: {exc.reason}") from exc
        except (http.client.HTTPException, ConnectionError) as exc:
            raise LocalLLMError(f"Ollama stream was interrupted: {exc}") from exc

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
                self._model_available_until = 0.0
                raise OllamaModelNotFoundError(body) from exc
            raise LocalLLMError(f"Ollama HTTP error {exc.code}: {body}") from exc
        except socket.timeout as exc:
            raise OllamaTimeoutError(f"Ollama request timed out after {self.timeout_seconds} seconds.") from exc
        except urllib.error.URLError as exc:
            raise OllamaConnectionError(f"Could not connect to local Ollama at {self.base_url}: {exc.reason}") from exc


def _response_socket(response: Any) -> socket.socket | None:
    """Return the socket behind an urllib response, if it can be reached."""
    raw = getattr(getattr(response, "fp", None), "raw", None)
    sock = getattr(raw, "_sock", None)
    return sock if isinstance(sock, socket.socket) else None


def nanoseconds_to_seconds(value: Any) -> float:
    if value is None:
        return 0.0
    return round(float(value) / 1_000_000_000, 3)


def optional_nanoseconds_to_seconds(value: Any) -> float | None:
    if value is None:
        return None
    return nanoseconds_to_seconds(value)
