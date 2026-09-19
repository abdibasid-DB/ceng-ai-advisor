# Raw Corpus Readiness

## Stage

Stage 8B - Manual Source Resolution

## Summary

| Metric | Count |
|---|---:|
| Total approved sources | 56 |
| Locally available sources | 45 |
| Unresolved sources | 11 |
| HTML files | 40 |
| PDF files | 5 |
| Text files | 0 |
| Percentage locally available | 80.36% |

## Resolved During Stage 8B

Five previously manual-required sources were resolved with legitimate official same-organization PDF files:

- `src_016` - Linux Foundation 2024 State of Tech Talent Report
- `src_017` - World Economic Forum Future of Jobs Report 2025
- `src_031` - OECD A Skills-First Labour Market
- `src_045` - OECD Skills for the digital age
- `src_046` - OECD Economic Surveys: Türkiye 2025

All five files are stored in `knowledge_base/raw/pdf/` and passed basic PDF checks.

## Remaining Unresolved Sources

### Critical

None.

### Important

- `src_009` - ACM Curricula Recommendations
- `src_010` - BLS Software Developers, Quality Assurance Analysts, and Testers
- `src_011` - BLS Computer Hardware Engineers
- `src_012` - BLS Information Security Analysts
- `src_013` - BLS Computer and Information Research Scientists
- `src_032` - Eurofound Working anytime, anywhere
- `src_042` - ACM CCECC Curricular Guidance
- `src_043` - UIUC ECE Subdisciplines

These sources would improve authority and detail, but they overlap with already available local evidence.

### Supplementary

- `src_047` - OECD Education GPS Türkiye profile
- `src_055` - ACM ITiCSE workload stress paper
- `src_056` - ACM CHI beginning programmers and code LLMs paper

These sources are useful but not essential because related evidence is already available locally.

## Coverage Basis

The locally available corpus includes enough evidence for the project guideline's major knowledge areas:

- Computer Engineering department information
- curriculum/course information
- programming and beginner concerns
- mathematics requirements and study concerns
- student life and wellbeing
- career opportunities
- Turkey employment and ICT sector evidence
- salary context, with limitations preserved
- AI and future technologies
- cybersecurity
- internships and career readiness
- skills and technologies
- graduate studies
- specializations
- remote work and international careers
- entrepreneurship
- work-life balance
- common misconceptions

The unresolved sources should remain listed for possible later improvement, but they do not block preprocessing.

## Readiness Decision

**A. RAW CORPUS SUFFICIENT FOR PREPROCESSING**

This decision is based on evidence coverage and source importance, not on acquiring every approved source. The current local raw corpus contains 45 sources and preserves the limitations of the 11 unresolved sources. Preprocessing can proceed in a later stage, provided the future pipeline records unresolved-source limitations and does not claim unavailable source content.

## Conditions for Proceeding

Before preprocessing:

1. Keep `docs/manual-source-acquisition.md` available for optional later manual downloads.
2. Keep `docs/unresolved-source-impact.md` available so unanswered source gaps remain visible.
3. During preprocessing, process only files that actually exist locally.
4. Do not create placeholder content for unresolved sources.
5. Preserve source IDs and `raw_file_path` metadata for traceability.

## Do Not Do Yet

This readiness decision does not start:

- cleaning;
- deduplication;
- chunking;
- embeddings;
- ChromaDB;
- Ollama;
- RAG;
- chatbot development;
- frontend or backend feature development.
