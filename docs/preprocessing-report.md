# Preprocessing Report

## Stage

Stage 9 - Document Preprocessing and Cleaning

## Scope

This stage processed only the 45 locally available raw source files recorded in `knowledge_base/sources.json`.

This stage did not create retrieval chunks, embeddings, ChromaDB, semantic retrieval, Ollama integration, RAG logic, chatbot functionality, or frontend/backend features.

## Inputs

- Approved sources: 56
- Locally available raw sources: 45
- Raw HTML files: 40
- Raw PDF files: 5
- Raw text files: 0
- Unresolved sources skipped: 11

Raw files were not modified.

## Output Structure

Processed source-level documents are stored in:

```text
knowledge_base/processed/documents/
```

The processing manifest is stored at:

```text
knowledge_base/processed/processing_manifest.json
```

Each successfully extracted source has one processed document:

```text
knowledge_base/processed/documents/src_XXX.txt
```

No retrieval chunks were created.

## Libraries Used

- Python standard library:
  - `html.parser`
  - `re`
  - `json`
  - `hashlib`
  - `pathlib`
- `pypdf` for local PDF text extraction

`requirements.txt` was updated with:

```text
pypdf
```

No AI, RAG, vector database, embedding, LangChain, LlamaIndex, ChromaDB, Ollama, or Sentence Transformers dependencies were added.

## HTML Extraction Method

HTML files were processed with a conservative custom parser based on Python's `html.parser`.

The parser:

- ignores script, style, noscript, SVG, canvas, form, iframe, nav, and footer content;
- preserves headings, paragraph-like blocks, list text, table text, and visible page content;
- extracts page title where available;
- keeps source identity by prepending `Source ID` and title information;
- removes obvious interface lines such as cookie notices, navigation labels, social/share lines, and modal/exit-dialog text where safely identifiable.

The cleaning intentionally remains conservative. If text could be meaningful, it is generally preserved.

## PDF Extraction Method

PDF files were processed with `pypdf.PdfReader`.

The extractor:

- reads pages in original order;
- prefixes extracted text with page numbers;
- preserves extracted headings, paragraphs, tables, lists, and section order as much as `pypdf` text extraction allows;
- does not use OCR;
- does not fabricate text when a PDF cannot be parsed.

One PDF, `src_046.pdf`, failed because the file is structurally incomplete and does not contain a valid EOF marker.

## Normalization Rules

The script applies conservative normalization:

- normalizes line endings to `\n`;
- removes zero-width characters;
- normalizes Unicode non-breaking spaces;
- collapses repeated spaces;
- collapses excessive blank lines;
- preserves paragraph separation;
- removes repeated short boilerplate lines;
- does not summarize, paraphrase, translate, rewrite, or add facts.

## Boilerplate Removal Method

The script uses:

- HTML tag skipping for obvious non-content elements;
- exact-line filters for common navigation and cookie text;
- regex filters for repeated website interface lines;
- simple navigation-line detection for short lines dominated by navigation terms.

This is intentionally not aggressive. The processed text may still contain some page chrome, but the main content is preserved where extractable.

## Duplicate Detection Method

Duplicate detection was document-level only.

The script computes:

- normalized text SHA-256 fingerprints for exact duplicate detection;
- token-set similarity for near-duplicate detection.

No files are deleted automatically. Possible duplicates are only flagged in the manifest.

## Quality Validation Method

Every processed document is checked for:

- empty extraction;
- very short extraction;
- very low word count;
- possible error/login/access-denied markers;
- possible navigation/interface dominance;
- limited PDF text extraction.

Documents with serious extraction concerns are marked `manual_review_required`.

## Representative Test Results

Before the full run, the script was tested on:

- `src_001` - OSTIM Technical University HTML page
- `src_014` - O*NET professional/government-style HTML page
- `src_016` - Linux Foundation PDF report

Representative test result:

- Processed records: 3
- Statuses: 3 success
- File types: 2 HTML, 1 PDF
- Total extracted characters: 71,851
- Total extracted words: 10,062
- Duplicate flags: 0

Inspection showed:

- OSTIM HTML retained the department description and reduced most navigation;
- O*NET HTML retained occupational description and task content, with interface noise reduced;
- PDF extraction produced meaningful ordered report text with page markers.

## Full Run Results

| Metric | Count |
|---|---:|
| Total raw documents considered | 45 |
| Successfully processed | 36 |
| Processed with warnings | 0 |
| Manual review required | 8 |
| Failed | 1 |
| HTML documents processed | 40 |
| PDF documents processed | 5 |
| Processed `.txt` documents created | 44 |
| Total extracted characters | 1,916,658 |
| Total extracted words | 289,487 |
| Possible duplicate groups | 0 |

## Manual Review Documents

The following documents produced very short extracted text and require manual review before chunking:

| Source ID | Type | Reason |
|---|---|---|
| src_007 | HTML | Very short extraction; low word count |
| src_019 | HTML | Very short extraction; low word count |
| src_021 | HTML | Very short extraction; low word count |
| src_022 | HTML | Very short extraction; low word count |
| src_023 | HTML | Very short extraction; low word count |
| src_024 | HTML | Very short extraction; low word count |
| src_025 | HTML | Very short extraction; low word count |
| src_027 | HTML | Very short extraction; low word count |

These appear to be pages whose acquired raw HTML has limited static article text or mostly shell content.

## Failed Document

| Source ID | Type | Failure |
|---|---|---|
| src_046 | PDF | `PdfStreamError: Stream has ended unexpectedly` |

`src_046.pdf` has a valid PDF header but no valid EOF marker, so it appears incomplete or structurally damaged. The script did not fabricate replacement text.

## Duplicate Findings

No exact or near-duplicate source-level documents were flagged.

## Suspicious Extraction Findings

Suspicious extraction findings are the same as the manual-review and failed items above:

- 8 HTML documents with very short extracted text;
- 1 malformed PDF that could not be extracted.

## Raw Corpus Preservation Check

Raw file sizes were checked against `knowledge_base/raw/acquisition_manifest.json`.

Result:

```text
Raw file size check matched acquisition manifest for all local files.
```

This confirms the preprocessing script did not modify the raw corpus.

## Later-Stage Artifact Check

The following paths do not exist:

- `knowledge_base/processed/chunks`
- `knowledge_base/processed/embeddings`
- `knowledge_base/processed/vector_store`
- `chroma`
- `chroma_db`

No chunking, embeddings, vector database, Ollama, RAG, chatbot, frontend, or backend feature work was performed.

## Important Limitations

- HTML extraction uses conservative structural and line-based rules. Some residual boilerplate may remain.
- Some acquired HTML pages contain too little static source text to be useful without manual review.
- PDF extraction quality depends on embedded text quality. No OCR was used.
- `src_046.pdf` must be reacquired or manually resolved before it can be processed.
- The 11 unresolved raw sources from Stage 8B remain outside Stage 9 and were not processed.

## Rerun Command

```powershell
python scripts\preprocess_sources.py
```

## Readiness Decision

**B. PREPROCESSING ISSUES MUST BE RESOLVED BEFORE CHUNKING**

Reason: although 36 documents processed cleanly and 44 `.txt` files were created, 8 documents require manual review due very short extraction and 1 PDF failed extraction. These issues should be reviewed or explicitly excluded before Stage 10 chunking begins.
