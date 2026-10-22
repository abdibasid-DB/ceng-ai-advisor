"""Create retrieval-ready chunks from preprocessed knowledge-base documents.

Stage 10 only: this script creates chunk text and metadata. It does not create
embeddings, vector databases, retrieval code, Ollama integration, or chatbot
logic.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import statistics
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSING_MANIFEST_PATH = PROJECT_ROOT / "knowledge_base" / "processed" / "processing_manifest.json"
SOURCES_PATH = PROJECT_ROOT / "knowledge_base" / "sources.json"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "knowledge_base" / "chunks"

# ~180-word chunks keep almost every chunk inside the embedding model's
# 512-token window; the earlier 380/500/60 chunks lost text to truncation
# (Step 1.2, docs/retrieval-paraphrases-step-1-2/summary.md).
TARGET_WORDS = 180
MAX_WORDS = 220
OVERLAP_WORDS = 40
EXTREMELY_SHORT_WORDS = 40
OVERSIZED_WORDS = MAX_WORDS

REPRESENTATIVE_SAMPLE_IDS = ["src_001", "src_018", "src_017", "src_007"]

WORD_RE = re.compile(r"\S+")
SENTENCE_BOUNDARY_RE = re.compile(r"(?<=[.!?])\s+")

# Short digit-free HTML blocks found in the header or footer zone of at least
# this many different HTML documents are treated as navigation/menu
# boilerplate. Table rows (country names, percentages) sit mid-page and stay.
NAV_BLOCK_MAX_WORDS = 12
NAV_BLOCK_MIN_DOCUMENTS = 3
NAV_EDGE_SHARE = 0.2
# Repeated paragraphs inside one HTML page (pages rendered twice) are dropped
# from their second occurrence; short repeated labels such as place names are kept.
REPEATED_BLOCK_MIN_WORDS = 8
COOKIE_BLOCK_MAX_WORDS = 80
COOKIE_RE = re.compile(r"cookie|çerez|kvkk|gdpr|kabul et\b|accept all|strictly necessary", re.IGNORECASE)
PAGE_NUMBER_RE = re.compile(r"^page\s+\d+$", re.IGNORECASE)
SOURCE_ID_HEADER_RE = re.compile(r"^source id:\s*\S+$", re.IGNORECASE)


@dataclass
class TextUnit:
    text: str
    section_heading: str | None
    word_count: int


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def count_words(text: str) -> int:
    return len(WORD_RE.findall(text))


def count_characters(text: str) -> int:
    return len(text)


def stable_content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def normalize_block(text: str) -> str:
    lines = [line.strip() for line in text.splitlines()]
    lines = [line for line in lines if line]
    return "\n".join(lines).strip()


def split_blocks(text: str) -> list[str]:
    blocks = []
    for raw_block in re.split(r"\n\s*\n+", text.replace("\r\n", "\n")):
        block = normalize_block(raw_block)
        if block:
            blocks.append(block)
    return blocks


def block_key(block: str) -> str:
    return " ".join(block.split()).casefold()


def html_boilerplate_blocks(documents: list[tuple[dict[str, Any], str]]) -> set[str]:
    document_counts: Counter[str] = Counter()
    for record, text in documents:
        if record.get("input_file_type") != "html":
            continue
        blocks = split_blocks(text)
        edge = max(1, int(len(blocks) * NAV_EDGE_SHARE))
        edge_blocks = {
            block_key(block)
            for index, block in enumerate(blocks)
            if (index < edge or index >= len(blocks) - edge)
            and count_words(block) <= NAV_BLOCK_MAX_WORDS
            and not any(char.isdigit() for char in block)
        }
        document_counts.update(edge_blocks)
    return {block for block, count in document_counts.items() if count >= NAV_BLOCK_MIN_DOCUMENTS}


def clean_document(text: str, file_type: str, boilerplate: set[str]) -> str:
    """Drop source-id headers, page numbers, cookie banners, shared HTML navigation and repeated HTML paragraphs."""
    kept: list[str] = []
    seen_paragraphs: set[str] = set()
    for block in split_blocks(text):
        lines = [
            line
            for line in block.splitlines()
            if not SOURCE_ID_HEADER_RE.match(line.strip()) and not PAGE_NUMBER_RE.match(line.strip())
        ]
        block = "\n".join(lines).strip()
        if not block:
            continue
        key = block_key(block)
        words = count_words(block)
        if words <= COOKIE_BLOCK_MAX_WORDS and COOKIE_RE.search(block):
            continue
        if file_type == "html":
            if key in boilerplate:
                continue
            if words >= REPEATED_BLOCK_MIN_WORDS:
                if key in seen_paragraphs:
                    continue
                seen_paragraphs.add(key)
        kept.append(block)
    return "\n\n".join(kept) + "\n"


def looks_like_heading(block: str) -> bool:
    """Conservatively detect section headings without treating prose as headings."""
    compact = " ".join(block.split())
    words = WORD_RE.findall(compact)
    if not compact or "\n" in block:
        return False
    if len(words) > 14 or len(compact) > 120:
        return False
    lowered = compact.lower()
    if lowered.startswith(("source id:", "title:", "http://", "https://", "www.")):
        return False
    if re.fullmatch(r"page\s+\d+", lowered):
        return False
    if "@" in compact:
        return False
    if not re.search(r"[A-Za-zÇĞİÖŞÜçğıöşü]", compact):
        return False
    terminal_punctuation = compact.endswith((".", "?", "!"))
    title_like = compact.istitle() or compact.isupper()
    numbered_heading = bool(re.match(r"^\d+(\.\d+)*\s+\S+", compact))
    short_label = len(words) <= 6 and not terminal_punctuation
    return numbered_heading or title_like or short_label


def build_text_units(text: str) -> list[TextUnit]:
    blocks = split_blocks(text)
    units: list[TextUnit] = []
    pending_headings: list[str] = []
    active_heading: str | None = None

    for block in blocks:
        if looks_like_heading(block):
            pending_headings.append(block)
            active_heading = block
            continue

        if pending_headings:
            unit_text = "\n\n".join(pending_headings + [block])
            unit_heading = pending_headings[-1]
            pending_headings = []
        else:
            unit_text = block
            unit_heading = active_heading

        units.append(TextUnit(unit_text, unit_heading, count_words(unit_text)))

    if pending_headings:
        unit_text = "\n\n".join(pending_headings)
        units.append(TextUnit(unit_text, active_heading, count_words(unit_text)))

    return units


def split_oversized_unit(unit: TextUnit, max_words: int, overlap_words: int) -> list[TextUnit]:
    sentences = [sentence.strip() for sentence in SENTENCE_BOUNDARY_RE.split(unit.text) if sentence.strip()]
    pieces: list[TextUnit] = []

    if len(sentences) <= 1:
        words = WORD_RE.findall(unit.text)
        start = 0
        while start < len(words):
            end = min(start + max_words, len(words))
            text = " ".join(words[start:end]).strip()
            pieces.append(TextUnit(text, unit.section_heading, count_words(text)))
            if end == len(words):
                break
            start = max(0, end - overlap_words)
        return pieces

    current: list[str] = []
    current_words = 0
    for sentence in sentences:
        sentence_words = count_words(sentence)
        if sentence_words > max_words:
            if current:
                text = " ".join(current).strip()
                pieces.append(TextUnit(text, unit.section_heading, count_words(text)))
                current = []
                current_words = 0
            pieces.extend(split_oversized_unit(TextUnit(sentence, unit.section_heading, sentence_words), max_words, overlap_words))
            continue

        if current and current_words + sentence_words > max_words:
            text = " ".join(current).strip()
            pieces.append(TextUnit(text, unit.section_heading, count_words(text)))
            overlap = tail_words(text, overlap_words)
            current = [overlap, sentence] if overlap else [sentence]
            current_words = count_words(" ".join(current))
        else:
            current.append(sentence)
            current_words += sentence_words

    if current:
        text = " ".join(current).strip()
        pieces.append(TextUnit(text, unit.section_heading, count_words(text)))

    return pieces


def tail_words(text: str, word_count: int) -> str:
    words = WORD_RE.findall(text)
    if len(words) <= word_count:
        return ""
    return " ".join(words[-word_count:])


def create_chunks_from_units(
    units: list[TextUnit],
    *,
    target_words: int,
    max_words: int,
    overlap_words: int,
) -> list[TextUnit]:
    expanded_units: list[TextUnit] = []
    for unit in units:
        if unit.word_count > max_words:
            expanded_units.extend(split_oversized_unit(unit, max_words, overlap_words))
        else:
            expanded_units.append(unit)

    chunks: list[TextUnit] = []
    current_parts: list[str] = []
    current_heading: str | None = None

    def flush(with_overlap: bool) -> str:
        nonlocal current_parts, current_heading
        text = "\n\n".join(part for part in current_parts if part).strip()
        if text:
            chunks.append(TextUnit(text, current_heading, count_words(text)))
        overlap = tail_words(text, overlap_words) if with_overlap and count_words(text) >= target_words else ""
        current_parts = [overlap] if overlap else []
        current_heading = None
        return overlap

    for unit in expanded_units:
        if not unit.text.strip():
            continue

        current_text = "\n\n".join(current_parts).strip()
        current_words = count_words(current_text)
        would_exceed_max = current_parts and current_words + unit.word_count > max_words
        past_target_and_next_is_substantial = (
            current_parts
            and current_words >= target_words
            and unit.word_count >= max(40, overlap_words)
        )

        if would_exceed_max or past_target_and_next_is_substantial:
            overlap = flush(with_overlap=True)
            if overlap and (count_words(overlap) > unit.word_count or count_words(overlap) + unit.word_count > max_words):
                current_parts = []

        current_parts.append(unit.text)
        if unit.section_heading:
            current_heading = unit.section_heading

    flush(with_overlap=False)

    return merge_tiny_chunks([chunk for chunk in chunks if chunk.text.strip()], max_words=max_words)


def merge_tiny_chunks(chunks: list[TextUnit], max_words: int) -> list[TextUnit]:
    """Merge very small chunks with neighbors when doing so stays within max size."""
    merged: list[TextUnit] = []
    index = 0
    while index < len(chunks):
        chunk = chunks[index]

        if chunk.word_count >= EXTREMELY_SHORT_WORDS:
            merged.append(chunk)
            index += 1
            continue

        if merged and merged[-1].word_count + chunk.word_count <= max_words:
            previous = merged.pop()
            text = f"{previous.text}\n\n{chunk.text}".strip()
            merged.append(TextUnit(text, previous.section_heading or chunk.section_heading, count_words(text)))
            index += 1
            continue

        if index + 1 < len(chunks) and chunk.word_count + chunks[index + 1].word_count <= max_words:
            next_chunk = chunks[index + 1]
            text = f"{chunk.text}\n\n{next_chunk.text}".strip()
            merged.append(TextUnit(text, chunk.section_heading or next_chunk.section_heading, count_words(text)))
            index += 2
            continue

        merged.append(chunk)
        index += 1

    return merged


def source_lookup() -> dict[str, dict[str, Any]]:
    sources_data = load_json(SOURCES_PATH)
    return {source["source_id"]: source for source in sources_data["sources"]}


def get_eligible_records(processing_manifest: dict[str, Any], sample: bool) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    records = processing_manifest["records"]
    eligible = [record for record in records if record.get("chunking_eligible") is True]
    excluded = [record for record in records if record.get("chunking_eligible") is not True]
    if sample:
        sample_set = set(REPRESENTATIVE_SAMPLE_IDS)
        eligible = [record for record in eligible if record["source_id"] in sample_set]
    return eligible, excluded


def build_chunk_record(
    chunk: TextUnit,
    record: dict[str, Any],
    source: dict[str, Any],
    chunk_index: int,
) -> dict[str, Any]:
    source_id = record["source_id"]
    return {
        "chunk_id": f"{source_id}_chunk_{chunk_index:03d}",
        "source_id": source_id,
        "chunk_index": chunk_index,
        "text": chunk.text,
        "title": source.get("title") or record.get("title"),
        "source_name": source.get("source_name"),
        "source_type": source.get("source_type"),
        "url": source.get("url"),
        "publication_date": source.get("publication_date"),
        "category": source.get("category") or record.get("category"),
        "language": source.get("language") or record.get("language"),
        "processed_file_path": record.get("processed_file_path"),
        "raw_file_path": record.get("raw_file_path") or source.get("raw_file_path"),
        "section_heading": chunk.section_heading,
        "word_count": chunk.word_count,
        "character_count": count_characters(chunk.text),
        "content_sha256": stable_content_hash(chunk.text),
    }


def validate_chunks(
    chunks: list[dict[str, Any]],
    eligible_ids: set[str],
    excluded_ids: set[str],
    approved_ids: set[str],
) -> dict[str, Any]:
    chunk_ids = [chunk["chunk_id"] for chunk in chunks]
    duplicate_ids = len(chunk_ids) - len(set(chunk_ids))
    empty_chunks = sum(1 for chunk in chunks if not chunk["text"].strip())
    oversized = sum(1 for chunk in chunks if chunk["word_count"] > OVERSIZED_WORDS)
    extremely_short = sum(1 for chunk in chunks if chunk["word_count"] < EXTREMELY_SHORT_WORDS)
    missing_source_ids = sorted({chunk["source_id"] for chunk in chunks if chunk["source_id"] not in approved_ids})
    chunks_from_excluded = sorted({chunk["source_id"] for chunk in chunks if chunk["source_id"] in excluded_ids})
    chunks_from_ineligible = sorted({chunk["source_id"] for chunk in chunks if chunk["source_id"] not in eligible_ids})
    missing_urls = sorted({chunk["source_id"] for chunk in chunks if not chunk.get("url")})
    required_metadata = [
        "chunk_id",
        "source_id",
        "chunk_index",
        "text",
        "title",
        "source_name",
        "source_type",
        "url",
        "category",
        "language",
        "processed_file_path",
        "word_count",
        "character_count",
    ]
    missing_metadata = []
    for chunk in chunks:
        missing = [field for field in required_metadata if chunk.get(field) in (None, "")]
        if missing:
            missing_metadata.append({"chunk_id": chunk["chunk_id"], "missing": missing})

    return {
        "empty_chunk_count": empty_chunks,
        "oversized_chunk_count": oversized,
        "extremely_short_chunk_count": extremely_short,
        "duplicate_chunk_id_count": duplicate_ids,
        "missing_source_ids": missing_source_ids,
        "chunks_from_excluded_sources": chunks_from_excluded,
        "chunks_from_ineligible_sources": chunks_from_ineligible,
        "missing_url_source_ids": missing_urls,
        "missing_metadata_count": len(missing_metadata),
        "missing_metadata_examples": missing_metadata[:20],
    }


def write_outputs(output_dir: Path, chunks: list[dict[str, Any]], manifest: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    chunks_path = output_dir / "chunks.jsonl"
    manifest_path = output_dir / "chunking_manifest.json"

    with chunks_path.open("w", encoding="utf-8", newline="\n") as file:
        for chunk in chunks:
            file.write(json.dumps(chunk, ensure_ascii=False) + "\n")

    with manifest_path.open("w", encoding="utf-8", newline="\n") as file:
        json.dump(manifest, file, ensure_ascii=False, indent=2)
        file.write("\n")


def chunk_documents(sample: bool = False, output_dir: Path = DEFAULT_OUTPUT_DIR) -> dict[str, Any]:
    processing_manifest = load_json(PROCESSING_MANIFEST_PATH)
    sources = source_lookup()
    approved_ids = set(sources)
    eligible_records, excluded_records = get_eligible_records(processing_manifest, sample)
    eligible_ids = {record["source_id"] for record in eligible_records}
    excluded_ids = {record["source_id"] for record in excluded_records}

    all_eligible, _ = get_eligible_records(processing_manifest, sample=False)
    boilerplate = html_boilerplate_blocks(
        [
            (record, (PROJECT_ROOT / record["processed_file_path"]).read_text(encoding="utf-8"))
            for record in all_eligible
            if (PROJECT_ROOT / record["processed_file_path"]).exists()
        ]
    )

    all_chunks: list[dict[str, Any]] = []
    per_source: list[dict[str, Any]] = []

    for record in sorted(eligible_records, key=lambda item: item["source_id"]):
        source_id = record["source_id"]
        source = sources.get(source_id)
        warnings: list[str] = []

        if source is None:
            per_source.append(
                {
                    "source_id": source_id,
                    "processed_file_path": record.get("processed_file_path"),
                    "number_of_chunks": 0,
                    "total_source_words": record.get("extracted_word_count"),
                    "chunking_status": "failed",
                    "warnings": ["source_id not found in knowledge_base/sources.json"],
                }
            )
            continue

        processed_path = PROJECT_ROOT / record["processed_file_path"]
        if not processed_path.exists():
            per_source.append(
                {
                    "source_id": source_id,
                    "processed_file_path": record.get("processed_file_path"),
                    "number_of_chunks": 0,
                    "total_source_words": record.get("extracted_word_count"),
                    "chunking_status": "failed",
                    "warnings": ["processed document missing"],
                }
            )
            continue

        original_text = processed_path.read_text(encoding="utf-8")
        text = clean_document(original_text, record.get("input_file_type", ""), boilerplate)
        units = build_text_units(text)
        chunks = create_chunks_from_units(
            units,
            target_words=TARGET_WORDS,
            max_words=MAX_WORDS,
            overlap_words=OVERLAP_WORDS,
        )

        if not chunks:
            warnings.append("no chunks created")

        source_chunk_count = 0
        for index, chunk in enumerate(chunks, start=1):
            if chunk.word_count < EXTREMELY_SHORT_WORDS:
                warnings.append(f"chunk {index} below {EXTREMELY_SHORT_WORDS} words")
            if chunk.word_count > MAX_WORDS:
                warnings.append(f"chunk {index} above configured maximum")
            all_chunks.append(build_chunk_record(chunk, record, source, index))
            source_chunk_count += 1

        per_source.append(
            {
                "source_id": source_id,
                "processed_file_path": record.get("processed_file_path"),
                "number_of_chunks": source_chunk_count,
                "total_source_words": count_words(original_text),
                "words_after_cleaning": count_words(text),
                "chunking_status": "success" if source_chunk_count else "failed",
                "warnings": sorted(set(warnings)),
            }
        )

    word_counts = [chunk["word_count"] for chunk in all_chunks]
    validation = validate_chunks(all_chunks, eligible_ids, excluded_ids, approved_ids)
    one_chunk_documents = sum(1 for item in per_source if item["number_of_chunks"] == 1)
    multi_chunk_documents = sum(1 for item in per_source if item["number_of_chunks"] > 1)

    manifest = {
        "schema_version": "1.0",
        "stage": "Stage 10 - Document Chunking (Step 1.2 option f: 180-word cleaned chunks)",
        "processing_timestamp": utc_now(),
        "sample_run": sample,
        "chunking_configuration": {
            "unit": "words",
            "target_word_count": TARGET_WORDS,
            "maximum_word_count": MAX_WORDS,
            "overlap_word_count": OVERLAP_WORDS,
            "extremely_short_word_threshold": EXTREMELY_SHORT_WORDS,
            "cleaning": True,
        },
        "chunking_method": {
            "name": "structure_aware_word_chunking",
            "description": "Detect simple headings, preserve paragraph blocks, group related blocks up to the configured target/maximum size, split oversized blocks by sentence or word windows, and apply controlled word overlap across chunk boundaries.",
            "heading_handling": "Short title-like lines are attached to the following content and also stored as section_heading metadata when detected.",
            "paragraph_handling": "Blank-line-separated processed text blocks are preserved where possible.",
            "overlap_handling": f"A {OVERLAP_WORDS}-word tail overlap is applied only after chunks at or above the target size; overlap is skipped if it would dominate the next chunk.",
            "cleaning": "Before chunking, source-id header lines, 'Page N' lines and short cookie/consent blocks are removed; for HTML documents, short digit-free header/footer blocks shared by at least 3 HTML documents (navigation menus) and repeated paragraphs of 8+ words are removed.",
            "boilerplate_block_patterns": len(boilerplate),
        },
        "input_manifest": str(PROCESSING_MANIFEST_PATH.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "source_registry": str(SOURCES_PATH.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "eligible_source_count": len([record for record in processing_manifest["records"] if record.get("chunking_eligible") is True]),
        "processed_source_count": len(eligible_records),
        "excluded_source_count": len(excluded_records),
        "excluded_source_ids": sorted(excluded_ids),
        "total_chunk_count": len(all_chunks),
        "minimum_chunk_word_count": min(word_counts) if word_counts else 0,
        "maximum_chunk_word_count": max(word_counts) if word_counts else 0,
        "average_chunk_word_count": round(statistics.mean(word_counts), 2) if word_counts else 0,
        "median_chunk_word_count": round(statistics.median(word_counts), 2) if word_counts else 0,
        "documents_producing_one_chunk": one_chunk_documents,
        "documents_producing_multiple_chunks": multi_chunk_documents,
        "validation": validation,
        "per_source": per_source,
    }

    write_outputs(output_dir, all_chunks, manifest)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Chunk processed knowledge-base documents.")
    parser.add_argument("--sample", action="store_true", help="Chunk only the representative Stage 10 sample.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Output directory for chunks.jsonl and chunking_manifest.json.",
    )
    args = parser.parse_args()

    manifest = chunk_documents(sample=args.sample, output_dir=args.output_dir)
    summary = {
        "sample_run": manifest["sample_run"],
        "processed_source_count": manifest["processed_source_count"],
        "total_chunk_count": manifest["total_chunk_count"],
        "minimum_chunk_word_count": manifest["minimum_chunk_word_count"],
        "maximum_chunk_word_count": manifest["maximum_chunk_word_count"],
        "average_chunk_word_count": manifest["average_chunk_word_count"],
        "median_chunk_word_count": manifest["median_chunk_word_count"],
        "validation": manifest["validation"],
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
