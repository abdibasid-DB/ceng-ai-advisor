# Stage 13 - Retrieval Quality Report

## Purpose

Stage 13 builds the retrieval layer that will later supply evidence to a local LLM. It does not generate natural-language answers, create RAG prompts, integrate Ollama, build chatbot behavior, or add frontend features.

The retrieval flow is:

`user question` -> `query embedding` -> `ChromaDB search` -> `candidate chunks` -> `retrieval quality logic` -> `final retrieved context`

## Retrieval Architecture

The reusable retrieval module is implemented in `backend/app/rag/retriever.py`.

It:

- loads the persistent local ChromaDB collection `ceng_advisor_chunks`
- loads `sentence-transformers/all-MiniLM-L6-v2`
- creates normalized query embeddings
- queries ChromaDB with cosine distance
- converts distance to cosine similarity with `1 - distance`
- preserves chunk IDs and source metadata
- applies deterministic metadata-aware reranking
- applies lightweight diversity control
- returns structured retrieval results without generating answers

## Configuration

Configuration is stored in `backend/app/core/retrieval_config.py`.

| Setting | Value |
|---|---:|
| Default Top-K | 5 |
| Candidate Top-K | 12 |
| Category supplemental candidates | 3 per inferred category |
| Minimum similarity threshold | 0.30 |
| Minimum results above threshold | 2 |
| Maximum final results per source | 3 |

## Top-K Experiments

Top-3, Top-5, and Top-8 were considered conceptually during testing:

- Top-3 is concise but can miss secondary evidence for multi-topic questions.
- Top-5 gives enough room for source diversity while staying compact.
- Top-8 adds more context but introduces more repeated report chunks and weaker evidence.

Selected default: **Top-5**

Top-5 is the best baseline for the later RAG stage because it balances evidence coverage, readability, and noise control.

## Similarity Threshold

Unrelated test queries produced low top similarity scores:

| Query | Top similarity |
|---|---:|
| What is the best recipe for chocolate cake? | 0.210 |
| Who won the football match yesterday? | 0.254 |
| How do I repair a washing machine? | 0.105 |

Most relevant Computer Engineering questions scored above 0.39, while weaker but usable evidence often remained above 0.30.

Selected threshold: **0.30**

The retrieval layer marks evidence as insufficient/out-of-scope when:

- top similarity is below 0.30, or
- fewer than 2 retrieved chunks are at or above 0.30

This is a conservative guardrail, not a formal accuracy metric.

## Out-of-Scope Detection

Out-of-scope detection uses only retrieval evidence:

- top similarity score
- number of results above threshold
- no LLM judgment

The three unrelated test questions were correctly rejected.

## Metadata-Aware Retrieval

The retriever performs broad semantic search first. When query wording clearly indicates categories such as curriculum, programming, AI, cybersecurity, internships, remote work, or entrepreneurship, it also fetches a small number of category-filtered supplemental candidates.

This is deterministic and general. It does not hard-code individual source IDs and does not force OSTIM sources to dominate unrelated questions.

Metadata-aware reranking uses:

- category match boost
- official/source-type boost for university/program/curriculum-style queries
- title keyword boost

## Redundancy and Diversity

The retriever avoids excessive repetition by limiting final results to at most 3 chunks from the same source when enough alternatives exist.

It does not force every result to come from a different source because adjacent or same-source chunks can be legitimately useful, especially for long reports.

## Curriculum Investigation

Known issue from Stage 11/12:

General Brown CS course-advice chunks sometimes outranked OSTIM-specific curriculum evidence.

After metadata-aware reranking:

- Brown `src_039` still ranks first for the broad query "What courses are taught in Computer Engineering?"
- OSTIM `src_004` curriculum chunks now occupy ranks 2, 4, and 5.

This is improved but not perfect. The likely cause is that the Brown page is semantically close to "courses taught" and contains explicit course-advice language, while OSTIM curriculum chunks are dense course listings. Later RAG integration should prefer source/context display and may add a source-priority policy for questions explicitly asking about OSTIM.

## Cybersecurity Investigation

Cybersecurity retrieval remains only partially strong.

The returned chunks are broadly relevant because they mention future jobs, skills, security management, digital skills, and computing occupations. However, the corpus has limited direct cybersecurity-career evidence and no strong dedicated cybersecurity category chunks.

The weakness appears to come mainly from knowledge-base coverage, not ChromaDB indexing or embedding mapping. No stronger evidence was fabricated.

## Paraphrase Robustness

The programming paraphrase test performed well:

- Original: "What programming languages should a Computer Engineering student learn?"
- Paraphrase: "Which coding languages are most useful for someone studying Computer Engineering?"

Both retrieved programming, curriculum, and skills/technology evidence. This supports the project requirement that example questions are representative and users may phrase questions differently.

## Multi-Topic Testing

The multi-topic query:

"Should I focus more on GPA, projects, or internships when preparing for a software career?"

retrieved career-preparation, graduate/career, and programming evidence. It did not fully cover all three concepts equally, especially internships. This is acceptable for the retrieval layer but should be reviewed during RAG-context assembly.

## Evaluation Summary

The evaluation set contains 23 cases:

- Department Information
- Curriculum
- Programming
- Mathematics
- Career Opportunities
- Employment
- Artificial Intelligence
- Cybersecurity
- Internships
- Skills and Technologies
- Graduate Studies
- Specializations
- Future Technologies
- Remote Work
- Entrepreneurship
- Work-Life Balance
- Common Misconceptions
- Paraphrase
- Multi-topic
- Out-of-scope

Final qualitative counts:

| Label | Count |
|---|---:|
| Highly relevant | 14 |
| Relevant | 5 |
| Irrelevant | 1 |
| Correctly rejected | 3 |

The remaining irrelevant case is entrepreneurship. The available entrepreneurship evidence is sparse and does not rank well for the representative query about starting a technology company.

## Remaining Weaknesses

- Entrepreneurship evidence is weak.
- Cybersecurity evidence is broad rather than direct.
- Curriculum retrieval still ranks one general course-advice source above OSTIM curriculum chunks.
- Multi-topic retrieval may not cover every subtopic equally.
- The threshold is based on observed score separation, not labeled statistical validation.

## Validation

Completed checks:

- New Python files syntax-checked.
- Retrieval tests passed.
- Representative retrieval evaluation ran successfully.
- Persistent ChromaDB reload verified through retriever tests.
- Source traceability fields are preserved.
- Excluded source IDs do not appear in retrieval tests.
- No Ollama integration was added.
- No RAG answer generation was implemented.

## Commands

Run retrieval tests:

```powershell
python -m unittest tests.test_retriever
```

Run retrieval evaluation:

```powershell
python scripts\evaluate_retrieval.py --top-k 5
```

## Readiness Decision

**A. RETRIEVAL PIPELINE READY FOR LOCAL LLM/RAG INTEGRATION**
