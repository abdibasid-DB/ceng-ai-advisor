# CENG AI Advisor Knowledge Base Expansion Report

Generated: 2026-10-13

## Scope

This work expanded the knowledge base without changing the local Ollama model, answer-generation logic, or refusal guards. The current preprocessing, chunking, embedding, and ChromaDB architecture was preserved. A recoverable backup of the previous Chroma directory was created at:

`knowledge_base/vector_store/chroma_backup_20261013-193515`

The repository already had substantial uncommitted changes before this work began, including RAG/backend/frontend files, evaluation artifacts, and previous knowledge-base additions through `src_076`. Those changes were preserved and not reverted.

## Phase 1 Findings: Existing Knowledge Gaps

The existing source registry had 78 sources, but only 59 sources were represented in the indexed chunk set. Several registered sources had no raw file or were excluded from chunking, so the practical retrieval corpus was smaller than the registry suggested.

The pre-expansion indexed corpus had:

- Registered sources: 78
- Indexed/chunked sources: 59
- Indexed chunks: 1,116
- Embeddings: 1,116
- Chroma records: 1,116

Underrepresented areas by source count and retrieval behavior:

- Mathematics had only one registered source.
- Cybersecurity had only two registered sources.
- Future technologies had one primary category source, mostly a broad labor-market report.
- Discipline comparison material existed, but was concentrated in ACM/IEEE curriculum material rather than short student-facing comparison notes.
- Cloud, command line, FPGA, safe cybersecurity learning, OSTIM graduate study, and OSTIM international admission were thin or absent as targeted retrievable topics.
- Several broad areas were represented mainly by very large reports, which can retrieve relevant evidence but may not retrieve concise student-facing passages.

## 200-Question Evaluation Analysis

The completed evaluation in `docs/full-200-ceng-ai-advisor-evaluation-20261013-165928/` showed:

- Correct evidence-supported answers: 2/200
- Correct insufficient-information responses: 35/200
- Incorrect refusals where evidence appeared to exist: 40/200
- Unsupported, incorrect, or misleading answers: 123/200
- Runtime errors: 0/200

Important distinction: the retrieval-only harness found plausible expected evidence in 178/200 full-evaluation cases, while the end-to-end answer quality remained poor. The dominant failure mode was not simply missing documents. It was generated answers with uncited or weakly supported claims, plus brittle answerability/refusal guards.

Most common systematic failures from the full evaluation:

- 121 answered cases had uncited claims.
- 40 cases were incorrect refusals where likely evidence existed.
- 24 false refusals came from unsupported-claim guard mismatch.
- Several failures involved missing citation labels, incomplete/truncated generations, or overly strict comparison/prerequisite checks.

Interpretation:

- Missing knowledge existed in specific topics, especially math/ML, FPGA, cloud, cybersecurity pathways, command line, OSTIM admissions, and OSTIM graduate study.
- Many failures were retrieval or ranking weaknesses rather than complete absence of knowledge.
- Many more failures were generation/citation/guard failures and cannot be solved by adding documents alone.
- Some evaluator labels may be too strict where lexical support checks do not capture semantic support, but the broad pattern is valid: citation format is not proof of factual grounding.

## Phase 2 Sources Added

Sixteen targeted source records were added as `src_079` through `src_094`. Each source has a compact local text note under `knowledge_base/raw/text/` and `knowledge_base/processed/documents/`. The notes are paraphrased, source-linked summaries rather than copied full documents.

| ID | Category | Source | URL |
|---|---|---|---|
| `src_079` | curriculum | ABET, Criteria for Accrediting Engineering Programs, 2026-2027 | https://www.abet.org/accreditation/accreditation-criteria/criteria-for-accrediting-engineering-programs-2026-2027/ |
| `src_080` | common_misconceptions | ACM/IEEE, Computing Curricula 2020 | https://www.acm.org/binaries/content/assets/education/curricula-recommendations/cc2020.pdf |
| `src_081` | programming | IEEE Computer Society, SWEBOK Guide v4.0 | https://www.computer.org/education/bodies-of-knowledge/software-engineering |
| `src_082` | skills_and_technologies | NIST SP 800-145, Definition of Cloud Computing | https://csrc.nist.gov/pubs/sp/800/145/final |
| `src_083` | skills_and_technologies | Cisco, What Is Computer Networking? | https://www.cisco.com/site/us/en/learn/topics/networking/what-is-computer-networking.html |
| `src_084` | specializations | Altera, What Is an FPGA? | https://www.altera.com/what-is-an-fpga |
| `src_085` | cybersecurity | ACM/IEEE/AIS/IFIP, CSEC 2017 | https://cybered.acm.org/ |
| `src_086` | career_opportunities | U.S. BLS, Data Scientists | https://www.bls.gov/ooh/math/data-scientists.htm |
| `src_087` | future_technologies | GitHub Octoverse 2024 | https://github.blog/news-insights/octoverse/octoverse-2024/ |
| `src_088` | graduate_studies | OSTIM Computer Engineering English Thesis MSc syllabus | https://fbebilgisayar.ostimteknik.edu.tr/program-syllabus |
| `src_089` | department_information | OSTIM International Student Admission Directive | https://ird.ostimteknik.edu.tr/web/content/198099?download=true&unique=97234f0c84b6ad847cb59728a89f51636f3c7768 |
| `src_090` | skills_and_technologies | MIT CSAIL Missing Semester, The Shell | https://missing.csail.mit.edu/2020/course-shell/ |
| `src_091` | skills_and_technologies | NACE Career Readiness Competencies | https://naceweb.org/career-readiness/competencies/career-readiness-defined |
| `src_092` | mathematics | DeepLearning.AI Mathematics for ML/Data Science | https://www.deeplearning.ai/courses/mathematics-for-machine-learning-and-data-science-specialization/ |
| `src_093` | artificial_intelligence | Stanford Encyclopedia of Philosophy, Computing Machinery and Intelligence | https://plato.stanford.edu/entries/turing-test/ |
| `src_094` | cybersecurity | CISA/NICCS Cyber Career Pathways Tool | https://niccs.cisa.gov/workforce-development/cyber-career-pathways-tool |

## Categories Expanded

The source registry now has 94 sources. Category counts after expansion:

- employment: 13
- skills_and_technologies: 11
- student_life: 9
- curriculum: 8
- department_information: 5
- internships: 5
- graduate_studies: 5
- common_misconceptions: 5
- specializations: 4
- career_opportunities: 4
- cybersecurity: 4
- programming: 4
- artificial_intelligence: 4
- work_life_balance: 3
- remote_work: 3
- future_technologies: 2
- salaries: 2
- mathematics: 2
- entrepreneurship: 1

## Phase 3 Integration

Pipeline artifacts after expansion:

- Registered sources: 94
- Processed manifest records: 83
- Chunked/indexed sources: 75
- Excluded sources: 8
- Indexed chunks: 1,132
- Embeddings: 1,132
- Chroma records: 1,132

Validation results:

- Chunking: 0 empty chunks, 0 oversized chunks, 0 duplicate chunk IDs, 0 missing metadata records.
- Embeddings: 1,132 vectors, 384 dimensions, normalized, no NaN/Inf values, count matches chunks.
- Chroma: 1,132 indexed records, persistent reload count 1,132, sample documents and metadata present.

Implementation notes:

- `scripts/generate_embeddings.py` now sets `HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1`, matching the retriever's local/offline behavior and preventing unnecessary network checks.
- `scripts/build_vector_store.py` now reads expected chunk count and embedding dimension from the current embedding manifest instead of a stale hardcoded chunk count.
- `scripts/build_vector_store.py` writes the vector-store manifest through a temp file and `os.replace`, because the previous OneDrive reparse-point manifest could be read but not directly overwritten on Windows.
- A full preprocessing pass was interrupted because it spent excessive time reprocessing unrelated large PDFs with repeated font warnings. The new text sources were then processed in a focused way and appended to the existing manifest, preserving existing processed artifacts.

## Phase 4 Retrieval Validation

### 200-Question Retrieval Coverage

Baseline before expansion:

- Relevant evidence retrieved: 194/200
- `ok`: 188
- `incorrect_semantic_retrieval`: 6
- `answerability_gate_possible_false_reject`: 4
- `answerability_gap_unsupported_may_pass`: 2

After expansion:

- Relevant evidence retrieved: 196/200
- `ok`: 189
- `incorrect_semantic_retrieval`: 4
- `answerability_gate_possible_false_reject`: 5
- `answerability_gap_unsupported_may_pass`: 2

Artifacts:

- Before: `docs/kb-expansion-baseline-retrieval-20261013.json`
- After: `docs/kb-expansion-after-retrieval-20261013.json`

The fixed 200-question retrieval suite improved modestly. This is expected because baseline retrieval was already strong by this harness. The main value of this expansion is broader trustworthy coverage for unseen student questions, not gaming the 200-question set.

### Unseen Retrieval Check

Artifact: `docs/kb-expansion-unseen-retrieval-20261013.json`

All 10 unseen checks returned sufficient evidence. New targeted documents were top hits for:

- ML/math preparation: `src_092`
- FPGA/embedded systems: `src_084`
- Cloud foundations: `src_082`
- Safe cybersecurity learning: `src_085`, `src_094`
- OSTIM thesis MSc path: `src_088`
- OSTIM international admission verification: `src_089`
- Command-line importance: `src_090`
- AI replacement concerns: `src_093` appeared in the top three, alongside WEF and Stanford AI Index sources.

Discipline-comparison queries still tended to retrieve CE2016 (`src_067`) ahead of the new CC2020 note (`src_080`). This is not wrong, but if concise discipline comparisons are important, future retrieval tuning could boost `common_misconceptions` or `src_080` for comparison-style queries.

## Remaining Problems Requiring RAG Code Changes

The most important remaining issues are outside knowledge-base expansion:

1. Generated answers often contain factual claims without inline citations. This caused most full 200-question failures.
2. The answerability/unsupported-claim guard can reject usable evidence after retrieval.
3. Some comparison/prerequisite questions retrieve related evidence but are rejected because the guard requires exact comparative wording.
4. Citation labels are syntactically valid but do not guarantee claim-level support.
5. Multi-turn cases still fail from generation/guard behavior even when retrieval is plausible.
6. Some query profiles could be improved for targeted source ranking, especially discipline comparison and "which should I learn first" questions.

## Bottom Line

The knowledge base is broader and more trustworthy after this expansion, especially for conceptual CE comparisons, software engineering practice, cloud, networking, FPGA/embedded, cybersecurity, data science, AI-era concerns, command-line skills, graduate study, and OSTIM admissions context.

The expanded KB is retrievable by the current RAG pipeline, but the end-to-end advisor still needs RAG code improvements before answer quality can match retrieval coverage.
