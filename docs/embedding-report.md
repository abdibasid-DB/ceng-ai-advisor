# Stage 11 - Embedding Report

## Purpose

Embeddings convert text chunks into numeric vectors so semantically similar questions and knowledge-base chunks can be compared. This is required for the future RAG pipeline because user questions will not always use the exact same wording as the source documents.

This stage created local embedding artifacts only. It did not create ChromaDB collections, vector database integration, production retrieval APIs, Ollama integration, RAG logic, chatbot behavior, or frontend/backend features.

## Corpus Language

The chunk metadata shows 792 English chunks and no Turkish chunk records. Some source names and page titles include Turkish characters, but the chunked content used for embeddings is primarily English.

Embedding model decision: **English-focused**

## Selected Model

| Field | Value |
|---|---|
| Model | `sentence-transformers/all-MiniLM-L6-v2` |
| Provider/repository | Hugging Face / Sentence Transformers |
| Model type | Dense Sentence Transformers embedding model |
| Embedding dimension | 384 |
| Device used | CPU |
| Normalization | Enabled |
| Intended similarity metric | Cosine similarity |
| Batch size | 32 |

The selected model is lightweight, established, reproducible by name, suitable for semantic search, and practical for a student laptop.

## Alternatives Considered

- `sentence-transformers/all-mpnet-base-v2`: likely stronger quality, but larger and slower.
- `intfloat/e5-small-v2`: lightweight and retrieval-oriented, but requires query/document prefix conventions.
- `intfloat/e5-base-v2`: retrieval-oriented and stronger than the small variant, but larger and slower.

`all-MiniLM-L6-v2` was chosen as the best first baseline for this project stage.

## Generated Artifacts

| Artifact | Purpose |
|---|---|
| `knowledge_base/embeddings/embeddings.npy` | Local NumPy matrix containing chunk embeddings |
| `knowledge_base/embeddings/embedding_metadata.jsonl` | Row-to-chunk/source mapping metadata |
| `knowledge_base/embeddings/embedding_manifest.json` | Configuration, model details, validation, and generation summary |

## Generation Results

| Metric | Value |
|---|---:|
| Total chunks | 792 |
| Total embeddings | 792 |
| Embedding dimension | 384 |
| Generation time | 57.49 seconds |
| NaN values | 0 |
| Infinite values | 0 |
| Duplicate chunk IDs | 0 |
| Minimum vector norm | 0.9999998807907104 |
| Maximum vector norm | 1.0000001192092896 |

The vector norms are approximately 1.0 because embeddings were normalized during generation.

## Validation

Validation confirmed:

- `chunks.jsonl` was read without changing chunk text.
- Embedding count equals chunk count.
- Metadata rows equal embedding rows.
- Embedding dimensions are consistent.
- No NaN or infinite values exist.
- Embedding metadata preserves `embedding_index`, `chunk_id`, and `source_id`.
- Every embedding can be traced back to a chunk and source.
- The local similarity utility can embed a query and return Top-K chunk IDs and scores.
- No ChromaDB, vector database, Ollama, RAG, chatbot, or application feature was created.

## Representative Testing

Representative questions were tested across programming, curriculum, cybersecurity, careers, AI, and internships.

Strong results:

- AI/job-impact questions retrieved highly relevant WEF and OECD chunks.
- Internship questions retrieved highly relevant NACE internship chunks.
- Programming questions retrieved programming-course and language-related evidence.

Weaker results:

- Curriculum questions retrieved general course-guidance chunks above some OSTIM curriculum chunks.
- Cybersecurity questions retrieved partially relevant computing/security-management evidence but would benefit from stronger direct cybersecurity sources or metadata filtering.

These issues do not block the next stage, but they should be considered during vector database and retrieval evaluation.

## Commands

Regenerate embeddings:

```powershell
python scripts\generate_embeddings.py
```

Run the representative similarity test:

```powershell
python scripts\test_embedding_similarity.py --preset-stage11 --top-k 5
```

Run one custom query:

```powershell
python scripts\test_embedding_similarity.py "What programming languages should I learn?" --top-k 5
```

## Limitations

- This is not yet a vector database.
- This is not yet production retrieval.
- No final chatbot answers were generated.
- No quantitative accuracy metric is claimed because no labeled relevance dataset exists yet.
- Future vector database testing should evaluate metadata filters, source-priority rules, and category-aware retrieval.

## Readiness Decision

**A. EMBEDDINGS READY FOR VECTOR DATABASE INTEGRATION**
