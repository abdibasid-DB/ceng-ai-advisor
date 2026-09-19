# Stage 10 - Document Chunking Report

## Purpose

Chunking is required before embeddings and retrieval because the processed documents are too large and varied to retrieve as whole files. Smaller, source-traceable chunks allow a future semantic retrieval system to return focused evidence that can fit into a local LLM context window.

This stage only creates retrieval-ready text chunks and metadata. It does not create embeddings, a vector database, semantic retrieval, Ollama integration, RAG logic, chatbot behavior, or frontend/backend features.

## Inputs

- Source registry: `knowledge_base/sources.json`
- Processing manifest: `knowledge_base/processed/processing_manifest.json`
- Processed documents: `knowledge_base/processed/documents/`
- Chunking readiness summary: `docs/chunking-readiness.md`

The processing manifest identified 38 documents as `chunking_eligible: true` and 7 documents as excluded from chunking.

## Strategy

The chunking pipeline uses a structure-aware, word-based strategy:

1. Split processed text into blank-line-separated blocks.
2. Detect simple heading-like lines where possible.
3. Attach detected headings to the following content instead of separating them.
4. Preserve paragraph/block boundaries where possible.
5. Group related blocks until the target size is reached.
6. Split oversized blocks by sentence boundaries when possible.
7. Fall back to word windows only when a block or sentence is too large.
8. Apply controlled overlap between neighboring chunks when useful.
9. Preserve metadata needed for future retrieval, source attribution, and UI source display.

This approach was selected because the corpus contains short OSTIM pages, normal professional or government web pages, and long PDF reports. A fixed character-only splitter would be harder to explain and would be more likely to separate headings from the text they describe.

## Configuration

| Setting | Value |
|---|---:|
| Unit | Words |
| Target chunk size | 380 words |
| Maximum chunk size | 500 words |
| Overlap size | 60 words |
| Extremely short warning threshold | 40 words |

Overlap is applied as a tail overlap from the previous chunk only when the previous chunk reaches the target size. The overlap is skipped when it would exceed the maximum chunk size or dominate the next chunk. Paragraph boundaries are preferred, and oversized paragraphs are split only when necessary.

## Metadata

Each chunk in `knowledge_base/chunks/chunks.jsonl` includes:

- `chunk_id`
- `source_id`
- `chunk_index`
- `text`
- `title`
- `source_name`
- `source_type`
- `url`
- `publication_date`
- `category`
- `language`
- `processed_file_path`
- `raw_file_path`
- `section_heading`
- `word_count`
- `character_count`
- `content_sha256`

Missing publication dates remain `null` when not available from the accepted source metadata. No missing metadata was found for required traceability fields.

## Source Traceability

Every chunk can be traced through:

`chunk_id` -> `source_id` -> `processed_file_path` -> `raw_file_path` -> original `url`

Validation confirmed:

- No chunks from excluded documents.
- No chunks from ineligible documents.
- No chunks with unknown source IDs.
- No chunks missing source URLs.
- No duplicate chunk IDs.

## Representative Test

Before running the full corpus, the chunker was tested on:

| Source ID | Representative role | Result |
|---|---|---:|
| `src_001` | OSTIM university document | 1 chunk |
| `src_018` | Normal professional/government-style web document | 1 chunk |
| `src_017` | Large PDF/report | 189 chunks |
| `src_007` | Valid short document | 1 chunk |

Sample validation results:

- Empty chunks: 0
- Oversized chunks: 0
- Duplicate chunk IDs: 0
- Metadata problems: 0
- Extremely short chunks: 1

The extremely short sample chunk is front matter from a large report. It was flagged instead of silently removed because the stage instructions require questionable chunks to be documented rather than deleted.

## Final Statistics

| Metric | Count |
|---|---:|
| Chunking-eligible documents | 38 |
| Documents successfully chunked | 38 |
| Documents excluded | 7 |
| Total chunks created | 792 |
| Minimum chunk word count | 5 |
| Maximum chunk word count | 500 |
| Average chunk word count | 394.74 |
| Median chunk word count | 434 |
| Documents producing one chunk | 11 |
| Documents producing multiple chunks | 27 |
| Extremely short chunks | 4 |
| Oversized chunks | 0 |
| Empty chunks | 0 |
| Duplicate chunk IDs | 0 |
| Metadata/traceability problems | 0 |

## Quality Warnings

Four chunks are below the 40-word warning threshold:

- `src_017_chunk_001`: report cover/front matter.
- `src_045_chunk_001`: report cover/front matter.
- `src_045_chunk_300`: short table/page marker content from a large report.
- `src_051_chunk_008`: short final heading from the source page.

These were retained and documented because they are derived from real processed source text. They should be reviewed during embedding/retrieval evaluation; if they produce poor retrieval behavior, a later cleaning or chunk-filtering policy can be considered with documentation.

## Limitations

- Heading detection is conservative and based on processed plain text, so not every original document heading can be recovered.
- PDF text extraction may include page labels, cover matter, table fragments, and layout artifacts from the preprocessing stage.
- Some source pages still include minor website boilerplate that was preserved from preprocessing.
- Chunk quality should be re-evaluated after embeddings and retrieval tests, but this stage does not start embeddings.

## Validation

Completed validation checks:

- `scripts/chunk_documents.py` syntax check passed.
- `knowledge_base/chunks/chunking_manifest.json` is valid JSON.
- `knowledge_base/chunks/chunks.jsonl` contains valid JSON records.
- All 792 chunk IDs are unique.
- All chunks map to approved source IDs.
- Only `chunking_eligible` documents were used.
- All 38 eligible documents produced at least one chunk.
- All 7 excluded documents produced zero chunks.
- No embeddings directory, vector database directory, ChromaDB directory, Ollama integration, RAG logic, or chatbot feature was created.

## Reproducibility

The script uses deterministic source ordering and deterministic chunk IDs:

`src_001_chunk_001`, `src_001_chunk_002`, and so on.

Running the script again with the same processed corpus, metadata, and configuration recreates `chunks.jsonl` and `chunking_manifest.json` instead of appending duplicate records.

Rerun command:

```powershell
python scripts\chunk_documents.py
```

## Readiness Decision

**A. CHUNKED CORPUS READY FOR EMBEDDING DESIGN**

The chunked corpus covers all 38 eligible processed documents, preserves required source metadata, avoids chunks from excluded sources, and passes validation. The remaining quality warnings are documented and do not block the next design stage.
