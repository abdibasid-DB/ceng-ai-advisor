"""Preprocess locally acquired raw knowledge-base source documents.

Stage 9 scope only:
- extract text from existing raw HTML/PDF/text files
- conservatively normalize source-level documents
- save one processed .txt file per source
- write a processing manifest

This script does not chunk documents, generate embeddings, create vector stores,
or modify raw files.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
from collections import Counter
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
SOURCES_PATH = ROOT / "knowledge_base" / "sources.json"
PROCESSED_ROOT = ROOT / "knowledge_base" / "processed"
DOCUMENTS_DIR = PROCESSED_ROOT / "documents"
MANIFEST_PATH = PROCESSED_ROOT / "processing_manifest.json"

BLOCK_TAGS = {
    "address",
    "article",
    "aside",
    "blockquote",
    "br",
    "caption",
    "dd",
    "div",
    "dl",
    "dt",
    "figcaption",
    "figure",
    "footer",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "header",
    "hr",
    "li",
    "main",
    "nav",
    "ol",
    "p",
    "pre",
    "section",
    "table",
    "tbody",
    "td",
    "tfoot",
    "th",
    "thead",
    "tr",
    "ul",
}
SKIP_TAGS = {"script", "style", "noscript", "svg", "canvas", "iframe", "nav", "footer"}
NOISE_EXACT = {
    "about us",
    "academic staff",
    "skip to content",
    "skip to main content",
    "toggle navigation",
    "menu",
    "search",
    "close",
    "home",
    "home page",
    "obs",
    "ebys",
    "library",
    "lms",
    "student",
    "activities",
    "forms and documents",
    "workplace documents",
    "exam schedules",
    "course schedules",
    "course contents",
    "cookie settings",
    "accept all",
    "accept cookies",
    "privacy policy",
    "reject all",
    "analytics only",
    "cookie preferences",
    "contents",
    "overview",
    "don't ask again this session",
    "don’t ask again this session",
}
NAV_WORDS = {
    "about",
    "advanced",
    "career",
    "cluster",
    "crosswalks",
    "facebook",
    "find",
    "help",
    "home",
    "linkedin",
    "menu",
    "navigation",
    "occupations",
    "reddit",
    "related",
    "search",
    "share",
    "sites",
    "twitter",
    "x",
}
NOISE_PATTERNS = [
    re.compile(r"^copyright\s+\d{4}", re.I),
    re.compile(r"^all rights reserved", re.I),
    re.compile(r"^follow us", re.I),
    re.compile(r"^share this", re.I),
    re.compile(r"^subscribe", re.I),
    re.compile(r"^sign in", re.I),
    re.compile(r"^log in", re.I),
    re.compile(r"^we use cookies", re.I),
    re.compile(r"^for details, see cookie policy", re.I),
    re.compile(r"you will be leaving o\*net online", re.I),
    re.compile(r"^yes,? let", re.I),
    re.compile(r"^no,? stay", re.I),
    re.compile(r"^see the easy-read overview", re.I),
    re.compile(r"^ver la perspectiva", re.I),
    re.compile(r"saldr", re.I),
    re.compile(r"^s[ií], vamos", re.I),
    re.compile(r"^no, qu", re.I),
]


@dataclass
class ProcessingRecord:
    source_id: str
    raw_file_path: str
    processed_file_path: str | None
    input_file_type: str
    processing_status: str
    extraction_method: str
    raw_size: int
    extracted_character_count: int
    extracted_word_count: int
    title: str
    category: str
    language: str
    duplicate_flag: bool
    possible_duplicate_of: str | None
    chunking_eligible: bool
    warnings: list[str]
    processing_timestamp: str


ACCEPT_VALID_SHORT_DOCUMENTS = {"src_007"}
EXCLUDE_FROM_CHUNKING_AFTER_REVIEW = {"src_019", "src_021", "src_022", "src_023", "src_024", "src_027", "src_046", "src_124"}
# Data tables whose rows are meaningless without the column headers (the BLS
# "Software developers" row is only numbers): each row is written out as
# "header: value" pairs with the table caption.
TABLE_ROWS_WITH_HEADERS = {"src_095"}


class ConservativeHTMLTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.skip_depth = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in SKIP_TAGS:
            self.skip_depth += 1
            return
        if tag in BLOCK_TAGS:
            self.parts.append("\n")

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in SKIP_TAGS and self.skip_depth:
            self.skip_depth -= 1
            return
        if tag in BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self.skip_depth:
            return
        if data and data.strip():
            self.parts.append(data)

    def get_text(self) -> str:
        return "".join(self.parts)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel_path(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def load_sources() -> list[dict[str, Any]]:
    data = json.loads(SOURCES_PATH.read_text(encoding="utf-8"))
    sources = data.get("sources")
    if not isinstance(sources, list):
        raise ValueError("sources.json must contain a sources list")
    return sources


def detect_file_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return "pdf"
    if suffix in {".html", ".htm"}:
        return "html"
    if suffix == ".txt":
        return "text"
    return "unknown"


def decode_text(data: bytes) -> str:
    for encoding in ("utf-8", "utf-8-sig", "cp1254", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def render_tables_with_headers(raw: str) -> str:
    """Replace each <table> that has a header row by one line per body row.

    "Software developers: 2025 National Employment Matrix code: 15-1252;
    Employment, 2025: 1,717.8; ..." keeps every value next to its column name,
    so a chunk holding the row can be understood on its own.
    """

    def cell_text(fragment: str) -> str:
        return " ".join(html.unescape(re.sub(r"(?s)<[^>]+>", " ", fragment)).split())

    def render(match: re.Match[str]) -> str:
        table = match.group(0)
        caption_match = re.search(r"(?is)<caption[^>]*>(.*?)</caption>", table)
        caption = cell_text(caption_match.group(1)) if caption_match else ""
        headers: list[str] = []
        lines: list[str] = []
        for row in re.findall(r"(?is)<tr[^>]*>(.*?)</tr>", table):
            cells = re.findall(r"(?is)<(th|td)[^>]*>(.*?)</\1>", row)
            if not headers and cells and all(tag.lower() == "th" for tag, _ in cells):
                headers = [cell_text(content) for _, content in cells]
                continue
            values = [cell_text(content) for _, content in cells]
            if not headers or not values:
                continue
            pairs = [f"{header}: {value}" for header, value in zip(headers[1:], values[1:]) if value]
            line = f"{values[0]}: {'; '.join(pairs)}."
            lines.append(f"{caption} - {line}" if caption else line)
        if not headers:
            return table
        return "".join(f"<p>{html.escape(line)}</p>" for line in lines)

    return re.sub(r"(?is)<table\b.*?</table>", render, raw)


def extract_embedded_listing(raw: str) -> str:
    """Club listing that the SKS student-communities page keeps in inline JavaScript.

    The page draws its cards from `var CATS` (category names in several
    languages) and `var COMM` (name and category of each community), so the
    HTML text holds only the page frame.
    """
    category_block = raw[raw.find("var CATS"):raw.find("var COMM")]
    categories = {number: (turkish, english) for number, turkish, english in re.findall(r"(\d+):\{tr:'([^']*)',en:'([^']*)'", category_block)}
    listing = raw[raw.find("var COMM"):]
    communities = re.findall(r"\{n:'([^']*)',c:(\d+)", listing[: listing.find("];")])
    if not categories or not communities:
        return ""
    lines = [
        "OSTİM Technical University student communities (Öğrenci Toplulukları, student clubs and societies): "
        f"{len(communities)} communities in {len(categories)} categories."
    ]
    for number, (turkish, english) in categories.items():
        names = [name for name, category in communities if category == number]
        if names:
            lines.append(f"{english} ({turkish}) student communities: {'; '.join(names)}.")
    return "\n\n".join(lines)


# Pages whose content is page data rather than HTML text.
EMBEDDED_DATA_EXTRACTORS = {"src_122": extract_embedded_listing}


def extract_html(path: Path, source_id: str = "") -> str:
    raw = decode_text(path.read_bytes())
    if source_id in TABLE_ROWS_WITH_HEADERS:
        raw = render_tables_with_headers(raw)
    title_match = re.search(r"<title[^>]*>(.*?)</title>", raw, flags=re.I | re.S)
    title = ""
    if title_match:
        title = html.unescape(re.sub(r"\s+", " ", title_match.group(1))).strip()
    parser = ConservativeHTMLTextExtractor()
    parser.feed(raw)
    text = parser.get_text()
    fallback = extract_html_regex_fallback(raw)
    if word_count(text) < 80 and word_count(fallback) > max(120, word_count(text) * 2):
        text = fallback
    if source_id in EMBEDDED_DATA_EXTRACTORS:
        text = EMBEDDED_DATA_EXTRACTORS[source_id](raw) or text
    if title:
        text = f"{title}\n\n{text}"
    return text


def extract_html_regex_fallback(raw: str) -> str:
    text = raw
    text = re.sub(r"(?is)<(script|style|noscript|svg|canvas|iframe|nav|footer)\b.*?</\1>", "\n", text)
    text = re.sub(r"(?is)<br\s*/?>", "\n", text)
    text = re.sub(r"(?is)</(p|div|section|article|li|tr|td|th|h[1-6]|small|span)>", "\n", text)
    text = re.sub(r"(?is)<[^>]+>", "\n", text)
    return html.unescape(text)


def extract_pdf(path: Path) -> str:
    reader = PdfReader(str(path))
    pages: list[str] = []
    for index, page in enumerate(reader.pages, start=1):
        extracted = page.extract_text() or ""
        if extracted.strip():
            pages.append(f"Page {index}\n{extracted}")
        else:
            pages.append(f"Page {index}\n")
    return "\n\n".join(pages)


def extract_raw_text(path: Path) -> str:
    return decode_text(path.read_bytes())


def normalize_line(line: str) -> str:
    line = html.unescape(line)
    line = line.replace("\u00a0", " ")
    line = re.sub(r"[\t\r\f\v]+", " ", line)
    line = re.sub(r" {2,}", " ", line)
    return line.strip()


def is_noise_line(line: str) -> bool:
    lowered = line.strip().lower()
    if not lowered:
        return False
    if lowered in NOISE_EXACT:
        return True
    compact_words = set(re.findall(r"[a-zA-Z]{2,}", lowered))
    if len(line) < 180 and len(compact_words & NAV_WORDS) >= 4 and not re.search(r"[.!?]", line):
        return True
    if len(lowered) <= 2:
        return True
    return any(pattern.search(line) for pattern in NOISE_PATTERNS)


def normalize_text(text: str, title: str, source_id: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[\u200b\u200c\u200d]", "", text)
    raw_lines = [normalize_line(line) for line in text.split("\n")]
    lines: list[str] = []
    previous = ""
    repeated_counter: Counter[str] = Counter()
    for line in raw_lines:
        if not line:
            if lines and lines[-1] != "":
                lines.append("")
            continue
        if is_noise_line(line):
            continue
        repeated_counter[line.lower()] += 1
        if repeated_counter[line.lower()] > 8 and len(line) < 120:
            continue
        if line == previous and len(line) < 160:
            continue
        lines.append(line)
        previous = line

    cleaned = "\n".join(lines)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    header = f"Source ID: {source_id}\nTitle: {title}\n\n"
    if cleaned.lower().startswith(title.lower()):
        return f"Source ID: {source_id}\n\n{cleaned}\n"
    return f"{header}{cleaned}\n"


def word_count(text: str) -> int:
    return len(re.findall(r"\b[\w'-]+\b", text, flags=re.UNICODE))


def normalized_fingerprint(text: str) -> str:
    body = re.sub(r"^Source ID:.*?\n", "", text, flags=re.S)
    body = re.sub(r"\W+", " ", body.lower()).strip()
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def token_set(text: str) -> set[str]:
    body = re.sub(r"\W+", " ", text.lower())
    return {token for token in body.split() if len(token) > 3}


def quality_warnings(text: str, file_type: str) -> list[str]:
    warnings: list[str] = []
    lowered = text.lower()
    chars = len(text.strip())
    words = word_count(text)
    if chars == 0:
        warnings.append("extracted text is empty")
    if chars < 500:
        warnings.append("extracted text is very short")
    if words < 80:
        warnings.append("extracted word count is very low")
    for marker in ("access denied", "403 forbidden", "404 not found", "captcha", "login required"):
        if marker in lowered:
            warnings.append(f"possible error/login marker found: {marker}")
    if file_type == "pdf" and words < 500:
        warnings.append("PDF extraction produced limited text")
    nav_terms = sum(lowered.count(term) for term in ("menu", "navigation", "cookie", "subscribe", "sign in"))
    if nav_terms > max(20, words // 20):
        warnings.append("content may contain substantial navigation/interface boilerplate")
    return warnings


def status_for_warnings(warnings: list[str]) -> str:
    serious_markers = (
        "extracted text is empty",
        "extracted text is very short",
        "extracted word count is very low",
        "possible error/login marker",
        "PDF extraction produced limited text",
    )
    if any(any(marker in warning for marker in serious_markers) for warning in warnings):
        return "manual_review_required"
    return "warning" if warnings else "success"


def process_source(source: dict[str, Any]) -> ProcessingRecord:
    source_id = source["source_id"]
    raw_rel = source.get("raw_file_path")
    title = source.get("title") or ""
    category = source.get("category") or ""
    language = source.get("language") or ""
    timestamp = utc_now()
    if not raw_rel:
        raise ValueError(f"{source_id} has no raw_file_path")

    raw_path = ROOT / raw_rel
    processed_path = DOCUMENTS_DIR / f"{source_id}.txt"
    file_type = detect_file_type(raw_path)
    raw_size = raw_path.stat().st_size if raw_path.exists() else 0
    warnings: list[str] = []

    try:
        if not raw_path.exists():
            raise FileNotFoundError(raw_rel)
        if file_type == "html":
            extracted = extract_html(raw_path, source_id)
            method = "html_parser_conservative"
            if source_id in TABLE_ROWS_WITH_HEADERS:
                method = "html_parser_table_rows_with_headers"
            if source_id in EMBEDDED_DATA_EXTRACTORS:
                method = "embedded_page_data"
        elif file_type == "pdf":
            extracted = extract_pdf(raw_path)
            method = "pypdf_extract_text"
        elif file_type == "text":
            extracted = extract_raw_text(raw_path)
            method = "plain_text_read"
        else:
            raise ValueError(f"unsupported input file type: {raw_path.suffix}")

        cleaned = normalize_text(extracted, title, source_id)
        warnings = quality_warnings(cleaned, file_type)
        processed_path.write_text(cleaned, encoding="utf-8", newline="\n")
        status = status_for_warnings(warnings)
        if source_id in ACCEPT_VALID_SHORT_DOCUMENTS:
            status = "success"
            warnings.append("Stage 9B review: accepted as a valid short document")
        if source_id in EXCLUDE_FROM_CHUNKING_AFTER_REVIEW:
            status = "excluded_from_chunking"
            warnings.append("Stage 9B review: excluded from chunking because local raw content is not substantively usable")
        return ProcessingRecord(
            source_id=source_id,
            raw_file_path=raw_rel,
            processed_file_path=rel_path(processed_path),
            input_file_type=file_type,
            processing_status=status,
            extraction_method=method,
            raw_size=raw_size,
            extracted_character_count=len(cleaned),
            extracted_word_count=word_count(cleaned),
            title=title,
            category=category,
            language=language,
            duplicate_flag=False,
            possible_duplicate_of=None,
            chunking_eligible=(status in {"success", "warning"}),
            warnings=warnings,
            processing_timestamp=timestamp,
        )
    except Exception as exc:
        return ProcessingRecord(
            source_id=source_id,
            raw_file_path=raw_rel,
            processed_file_path=None,
            input_file_type=file_type,
            processing_status="excluded_from_chunking" if source_id in EXCLUDE_FROM_CHUNKING_AFTER_REVIEW else "failed",
            extraction_method="failed",
            raw_size=raw_size,
            extracted_character_count=0,
            extracted_word_count=0,
            title=title,
            category=category,
            language=language,
            duplicate_flag=False,
            possible_duplicate_of=None,
            chunking_eligible=False,
            warnings=[f"{type(exc).__name__}: {exc}"],
            processing_timestamp=timestamp,
        )


def apply_duplicate_detection(records: list[ProcessingRecord]) -> None:
    fingerprints: dict[str, str] = {}
    token_sets: dict[str, set[str]] = {}
    texts: dict[str, str] = {}
    for record in records:
        if record.processing_status == "failed" or not record.processed_file_path:
            continue
        text = (ROOT / record.processed_file_path).read_text(encoding="utf-8", errors="replace")
        texts[record.source_id] = text
        fp = normalized_fingerprint(text)
        if fp in fingerprints:
            record.duplicate_flag = True
            record.possible_duplicate_of = fingerprints[fp]
            record.warnings.append("exact normalized-text duplicate")
        else:
            fingerprints[fp] = record.source_id
        token_sets[record.source_id] = token_set(text)

    ids = list(token_sets)
    for idx, source_id in enumerate(ids):
        record = next(r for r in records if r.source_id == source_id)
        if record.duplicate_flag:
            continue
        a = token_sets[source_id]
        if len(a) < 100:
            continue
        for other_id in ids[:idx]:
            b = token_sets[other_id]
            if len(b) < 100:
                continue
            similarity = len(a & b) / max(1, len(a | b))
            if similarity >= 0.86:
                record.duplicate_flag = True
                record.possible_duplicate_of = other_id
                record.warnings.append(f"possible near-duplicate; token-set similarity {similarity:.2f}")
                break


def save_manifest(records: list[ProcessingRecord], merge: bool = False) -> None:
    """Write the manifest; with merge, replace only the given sources' records."""
    rows = [asdict(record) for record in records]
    if merge and MANIFEST_PATH.exists():
        updated = {row["source_id"]: row for row in rows}
        existing = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))["records"]
        known = {row["source_id"] for row in existing}
        rows = [updated.get(row["source_id"], row) for row in existing] + [row for row in rows if row["source_id"] not in known]
    payload = {
        "schema_version": "1.0",
        "generated_at": utc_now(),
        "document_count": len(rows),
        "records": rows,
    }
    MANIFEST_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def select_sources(sources: list[dict[str, Any]], ids: set[str] | None) -> list[dict[str, Any]]:
    available = [source for source in sources if source.get("raw_file_path")]
    if ids is None:
        return available
    return [source for source in available if source.get("source_id") in ids]


def main() -> int:
    parser = argparse.ArgumentParser(description="Preprocess local raw knowledge-base source files.")
    parser.add_argument("--source-id", action="append", help="Process only a specific source ID. Can be repeated.")
    args = parser.parse_args()

    DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
    sources = load_sources()
    selected = select_sources(sources, set(args.source_id) if args.source_id else None)
    records = [process_source(source) for source in selected]
    apply_duplicate_detection(records)
    # Processing a few sources must not drop the other sources from the manifest.
    save_manifest(records, merge=bool(args.source_id))

    status_counts = Counter(record.processing_status for record in records)
    type_counts = Counter(record.input_file_type for record in records)
    total_chars = sum(record.extracted_character_count for record in records)
    total_words = sum(record.extracted_word_count for record in records)
    print(
        json.dumps(
            {
                "processed_records": len(records),
                "statuses": dict(status_counts),
                "file_types": dict(type_counts),
                "total_characters": total_chars,
                "total_words": total_words,
                "duplicate_flags": sum(1 for record in records if record.duplicate_flag),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
