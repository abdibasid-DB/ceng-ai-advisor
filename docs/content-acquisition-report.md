# Content Acquisition Report

## Stage

Stage 8 - Content Acquisition

## Project

AI-Powered Computer Engineering Student Advisor

## Run Date

2026-08-30

## Purpose

This stage created the initial reproducible local raw corpus from the 56 approved source records in `knowledge_base/sources.json`.

This stage did not preprocess, clean aggressively, deduplicate, chunk, embed, create ChromaDB, configure Ollama, implement RAG, implement chatbot logic, or modify frontend/backend features.

## Acquisition Methodology

The acquisition script `scripts/acquire_sources.py`:

- loads only approved source records from `knowledge_base/sources.json`;
- retrieves only each exact approved source URL;
- does not crawl websites or follow unrelated internal links;
- uses deterministic filenames based on `source_id`;
- saves successful HTML content under `knowledge_base/raw/html/`;
- saves successful PDF content under `knowledge_base/raw/pdf/`;
- saves plain text content under `knowledge_base/raw/text/`;
- writes an acquisition manifest to `knowledge_base/raw/acquisition_manifest.json`;
- updates `raw_file_path` only when acquisition succeeds or a valid existing file is found;
- records failed or blocked sources as `manual_required`;
- uses HTTP status checks, request timeout, retry handling, a user-agent, encoding-safe binary writes, and basic integrity checks.

## Raw Storage Structure

```text
knowledge_base/raw/
  html/
  pdf/
  text/
  metadata/
  acquisition_manifest.json
```

The `metadata/` folder is reserved for later raw acquisition notes or source-specific metadata exports. It was created in this stage but not populated because the manifest is stored at `knowledge_base/raw/acquisition_manifest.json`.

## Summary

| Metric | Count |
|---|---:|
| Total approved sources | 56 |
| Automatically acquired | 40 |
| Manual acquisition required | 16 |
| Failed | 0 |
| Skipped existing | 0 |
| HTML files saved | 40 |
| PDF files saved | 0 |
| Other text files saved | 0 |
| `sources.json` `raw_file_path` values updated | 40 |

No direct PDF source URLs were present in the approved source registry. The DOI sources may later be manually saved as HTML landing pages or legally available PDFs if accessible.

## Acquisition Problems

Automatic acquisition was blocked or rejected for 16 sources:

- `src_009`: HTTP 403 Forbidden
- `src_010`: HTTP 403 Forbidden
- `src_011`: HTTP 403 Forbidden
- `src_012`: HTTP 403 Forbidden
- `src_013`: HTTP 403 Forbidden
- `src_016`: HTTP 200 returned, but content resembled an error/login/bot-block page
- `src_017`: HTTP 403 Forbidden
- `src_031`: HTTP 403 Forbidden
- `src_032`: HTTP 429 Too Many Requests
- `src_042`: HTTP 200 returned, but content resembled an error/login/bot-block page
- `src_043`: HTTP 200 returned, but content resembled an error/login/bot-block page
- `src_045`: HTTP 403 Forbidden
- `src_046`: HTTP 403 Forbidden
- `src_047`: HTTP 403 Forbidden
- `src_055`: HTTP 403 Forbidden
- `src_056`: HTTP 403 Forbidden

These sources are documented in `docs/manual-source-acquisition.md`.

## Websites That Blocked Automated Access

The following organizations/sites blocked automated retrieval or returned content that failed integrity checks:

- ACM / ACM-related curriculum sites
- U.S. Bureau of Labor Statistics
- Linux Foundation
- World Economic Forum
- OECD
- Eurofound
- University of Illinois ECE
- ACM DOI resolver / ACM Digital Library DOI URLs

## Integrity Checks

Basic checks were performed only to confirm that saved raw files are plausible source content:

- files are not empty;
- HTML/text files are not suspiciously short;
- HTML files resemble actual HTML documents;
- common error/login/block markers are not present in the initial content sample;
- PDF files, if any, must begin with `%PDF-` and have plausible file size.

## Integrity-Check Failures

Three URLs returned HTTP 200 responses but were not saved as valid raw content because the content resembled a possible error, login, or bot-block page:

- `src_016`
- `src_042`
- `src_043`

No saved raw files failed integrity checks after being written.

## Files Created

- `scripts/acquire_sources.py`
- `knowledge_base/raw/html/`
- `knowledge_base/raw/pdf/`
- `knowledge_base/raw/text/`
- `knowledge_base/raw/metadata/`
- `knowledge_base/raw/acquisition_manifest.json`
- `docs/manual-source-acquisition.md`
- `docs/content-acquisition-report.md`

## Files Modified

- `knowledge_base/sources.json`

## Rerun Command

Use this command to rerun acquisition without overwriting already acquired files:

```powershell
python scripts\acquire_sources.py --timeout 25 --retries 1
```

Use this command only when intentionally replacing existing acquired files:

```powershell
python scripts\acquire_sources.py --timeout 25 --retries 1 --overwrite
```

## Next Stage Boundary

The raw corpus has been acquired as far as automatic retrieval allows. The next appropriate project stage is content acquisition review or manual acquisition of blocked sources, followed later by preprocessing. Preprocessing has not started.
