"""Acquire approved raw knowledge-base sources.

This script retrieves only the exact URLs already accepted in
knowledge_base/sources.json. It stores raw files deterministically by source_id,
records every outcome in an acquisition manifest, and updates raw_file_path only
for successful or already-existing acquisitions.
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
SOURCES_PATH = ROOT / "knowledge_base" / "sources.json"
RAW_ROOT = ROOT / "knowledge_base" / "raw"
HTML_DIR = RAW_ROOT / "html"
PDF_DIR = RAW_ROOT / "pdf"
TEXT_DIR = RAW_ROOT / "text"
METADATA_DIR = RAW_ROOT / "metadata"
MANIFEST_PATH = RAW_ROOT / "acquisition_manifest.json"

USER_AGENT = (
    "Mozilla/5.0 (compatible; CENG-AI-Advisor-SourceAcquisition/1.0; "
    "+local-university-project)"
)
MAX_DOWNLOAD_BYTES = 80 * 1024 * 1024


@dataclass
class AcquisitionResult:
    source_id: str
    original_url: str
    status: str
    acquisition_method: str
    local_file_path: str | None
    file_type: str | None
    http_status: int | None
    content_length: int | None
    acquisition_timestamp: str
    error: str | None
    notes: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "original_url": self.original_url,
            "status": self.status,
            "acquisition_method": self.acquisition_method,
            "local_file_path": self.local_file_path,
            "file_type": self.file_type,
            "http_status": self.http_status,
            "content_length": self.content_length,
            "acquisition_timestamp": self.acquisition_timestamp,
            "error": self.error,
            "notes": self.notes,
        }


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel_path(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def ensure_dirs() -> None:
    for directory in (HTML_DIR, PDF_DIR, TEXT_DIR, METADATA_DIR):
        directory.mkdir(parents=True, exist_ok=True)


def load_sources() -> dict[str, Any]:
    with SOURCES_PATH.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    sources = data.get("sources")
    if not isinstance(sources, list):
        raise ValueError("knowledge_base/sources.json must contain a sources list")
    return data


def save_sources(data: dict[str, Any]) -> None:
    tmp_path = SOURCES_PATH.with_suffix(".json.tmp")
    with tmp_path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    os.replace(tmp_path, SOURCES_PATH)


def save_manifest(results: list[AcquisitionResult]) -> None:
    manifest = {
        "schema_version": "1.0",
        "generated_at": utc_now(),
        "source_count": len(results),
        "results": [result.as_dict() for result in results],
    }
    tmp_path = MANIFEST_PATH.with_suffix(".json.tmp")
    with tmp_path.open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    os.replace(tmp_path, MANIFEST_PATH)


def choose_file_type(url: str, content_type: str | None, body_start: bytes) -> tuple[str, Path]:
    parsed_path = urlparse(url).path.lower()
    guessed_type, _ = mimetypes.guess_type(parsed_path)
    normalized = (content_type or guessed_type or "").lower()

    if "application/pdf" in normalized or parsed_path.endswith(".pdf") or body_start.startswith(b"%PDF"):
        return "pdf", PDF_DIR
    if normalized.startswith("text/plain"):
        return "text", TEXT_DIR
    return "html", HTML_DIR


def integrity_notes(path: Path, file_type: str) -> tuple[bool, str]:
    if not path.exists():
        return False, "file does not exist after acquisition"
    size = path.stat().st_size
    if size == 0:
        return False, "file is empty"

    if file_type == "pdf":
        with path.open("rb") as handle:
            header = handle.read(5)
        if header != b"%PDF-":
            return False, "file does not have a valid PDF header"
        if size < 1024:
            return False, "PDF file size is suspiciously small"
        return True, "PDF header and file size passed basic integrity checks"

    sample = path.read_bytes()[:4096].lower()
    error_markers = (
        b"404 not found",
        b"403 forbidden",
        b"access denied",
        b"login",
        b"captcha",
        b"cloudflare",
    )
    if len(sample.strip()) < 200:
        return False, "text/html content is suspiciously short"
    if any(marker in sample for marker in error_markers):
        return False, "text/html content contains possible error, login, or bot-block marker"
    if file_type == "html" and b"<html" not in sample and b"<!doctype html" not in sample:
        return False, "HTML file does not look like an HTML document"
    return True, "text/html content passed basic integrity checks"


def existing_result(source: dict[str, Any]) -> AcquisitionResult | None:
    source_id = source["source_id"]
    for file_type, directory, suffix in (
        ("html", HTML_DIR, ".html"),
        ("pdf", PDF_DIR, ".pdf"),
        ("text", TEXT_DIR, ".txt"),
    ):
        candidate = directory / f"{source_id}{suffix}"
        if candidate.exists():
            ok, note = integrity_notes(candidate, file_type)
            status = "skipped_existing" if ok else "failed"
            error = None if ok else note
            return AcquisitionResult(
                source_id=source_id,
                original_url=source.get("url", ""),
                status=status,
                acquisition_method="existing_file",
                local_file_path=rel_path(candidate) if ok else None,
                file_type=file_type if ok else None,
                http_status=None,
                content_length=candidate.stat().st_size,
                acquisition_timestamp=utc_now(),
                error=error,
                notes=note,
            )
    return None


def fetch_url(url: str, timeout: int) -> tuple[int, str | None, bytes]:
    request = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/pdf,text/plain;q=0.9,*/*;q=0.8",
        },
        method="GET",
    )
    with urlopen(request, timeout=timeout) as response:
        status = getattr(response, "status", None) or response.getcode()
        content_type = response.headers.get("Content-Type")
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = response.read(64 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > MAX_DOWNLOAD_BYTES:
                raise ValueError(f"download exceeds {MAX_DOWNLOAD_BYTES} bytes")
            chunks.append(chunk)
    return int(status), content_type, b"".join(chunks)


def acquire_one(source: dict[str, Any], timeout: int, retries: int, overwrite: bool) -> AcquisitionResult:
    source_id = source.get("source_id")
    url = source.get("url")
    if not source_id or not url:
        return AcquisitionResult(
            source_id=source_id or "unknown",
            original_url=url or "",
            status="failed",
            acquisition_method="validation",
            local_file_path=None,
            file_type=None,
            http_status=None,
            content_length=None,
            acquisition_timestamp=utc_now(),
            error="source record is missing source_id or url",
            notes="No acquisition attempted.",
        )

    if not overwrite:
        existing = existing_result(source)
        if existing is not None:
            return existing

    last_error: str | None = None
    http_status: int | None = None
    for attempt in range(1, retries + 2):
        try:
            status, content_type, body = fetch_url(url, timeout)
            http_status = status
            if status < 200 or status >= 300:
                raise ValueError(f"HTTP status {status}")
            if not body:
                raise ValueError("empty response body")

            file_type, directory = choose_file_type(url, content_type, body[:32])
            suffix = ".pdf" if file_type == "pdf" else ".txt" if file_type == "text" else ".html"
            target = directory / f"{source_id}{suffix}"
            tmp_target = target.with_suffix(target.suffix + ".tmp")
            tmp_target.write_bytes(body)

            ok, note = integrity_notes(tmp_target, file_type)
            if not ok:
                tmp_target.unlink(missing_ok=True)
                return AcquisitionResult(
                    source_id=source_id,
                    original_url=url,
                    status="manual_required",
                    acquisition_method="http_get",
                    local_file_path=None,
                    file_type=file_type,
                    http_status=http_status,
                    content_length=len(body),
                    acquisition_timestamp=utc_now(),
                    error=note,
                    notes="Automatic acquisition completed but integrity checks failed; manual review required.",
                )

            os.replace(tmp_target, target)
            return AcquisitionResult(
                source_id=source_id,
                original_url=url,
                status="success",
                acquisition_method="http_get",
                local_file_path=rel_path(target),
                file_type=file_type,
                http_status=http_status,
                content_length=len(body),
                acquisition_timestamp=utc_now(),
                error=None,
                notes=note,
            )
        except HTTPError as exc:
            http_status = exc.code
            last_error = f"HTTPError {exc.code}: {exc.reason}"
        except (URLError, TimeoutError, ValueError, OSError) as exc:
            last_error = f"{type(exc).__name__}: {exc}"

        if attempt <= retries:
            time.sleep(1.5 * attempt)

    return AcquisitionResult(
        source_id=source_id,
        original_url=url,
        status="manual_required",
        acquisition_method="http_get",
        local_file_path=None,
        file_type=None,
        http_status=http_status,
        content_length=None,
        acquisition_timestamp=utc_now(),
        error=last_error,
        notes="Automatic acquisition failed after retry handling; manual review required.",
    )


def select_sources(sources: list[dict[str, Any]], source_ids: set[str] | None, limit: int | None) -> list[dict[str, Any]]:
    selected = sources
    if source_ids is not None:
        selected = [source for source in selected if source.get("source_id") in source_ids]
    if limit is not None:
        selected = selected[:limit]
    return selected


def update_raw_paths(sources: list[dict[str, Any]], results: list[AcquisitionResult]) -> int:
    by_id = {result.source_id: result for result in results}
    updated = 0
    for source in sources:
        result = by_id.get(source.get("source_id"))
        if result and result.status in {"success", "skipped_existing"} and result.local_file_path:
            if source.get("raw_file_path") != result.local_file_path:
                source["raw_file_path"] = result.local_file_path
                updated += 1
    return updated


def main() -> int:
    parser = argparse.ArgumentParser(description="Acquire approved raw source content.")
    parser.add_argument("--source-id", action="append", help="Acquire only a specific source ID. Can be repeated.")
    parser.add_argument("--limit", type=int, help="Acquire only the first N selected sources.")
    parser.add_argument("--overwrite", action="store_true", help="Replace existing acquired files.")
    parser.add_argument("--timeout", type=int, default=25, help="HTTP timeout in seconds.")
    parser.add_argument("--retries", type=int, default=1, help="Retry count after the first HTTP attempt.")
    args = parser.parse_args()

    ensure_dirs()
    data = load_sources()
    sources = data["sources"]
    selected = select_sources(sources, set(args.source_id) if args.source_id else None, args.limit)
    if not selected:
        print("No sources selected.", file=sys.stderr)
        return 2

    results: list[AcquisitionResult] = []
    for source in selected:
        result = acquire_one(source, timeout=args.timeout, retries=args.retries, overwrite=args.overwrite)
        results.append(result)
        print(f"{result.source_id}: {result.status} ({result.file_type or 'none'})")

    updated = update_raw_paths(sources, results)
    save_sources(data)
    save_manifest(results)

    status_counts: dict[str, int] = {}
    for result in results:
        status_counts[result.status] = status_counts.get(result.status, 0) + 1

    print(json.dumps({"processed": len(results), "raw_file_paths_updated": updated, "statuses": status_counts}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
