# Stage 11 - Embedding Model Selection

## Corpus Language Assessment

The chunk metadata was inspected before model selection.

| Language metadata | Chunk count |
|---|---:|
| English | 792 |

All chunk records in `knowledge_base/chunks/chunks.jsonl` are marked as English. Some source titles and institution names include Turkish characters because OSTIM Technical University pages are connected to Türkiye, but the chunk text available for embedding is primarily English.

Decision: **A. English-focused embedding model**

A multilingual model is not required for the current chunked corpus. If Turkish sources are later added and chunked, this decision should be reviewed.

## Candidate Models Considered

| Model | Dimension | Strengths | Trade-offs | Suitability |
|---|---:|---|---|---|
| `sentence-transformers/all-MiniLM-L6-v2` | 384 | Lightweight, well established, fast on CPU, designed for sentence/document semantic similarity, easy to use with Sentence Transformers | Lower capacity than larger models | Strong fit for a student laptop and English semantic search |
| `sentence-transformers/all-mpnet-base-v2` | 768 | Often higher semantic retrieval quality than MiniLM | Larger, slower, more memory use | Good quality option, but heavier than needed for this stage |
| `intfloat/e5-small-v2` | 384 | Lightweight, strong retrieval-oriented model family | Requires careful query/document prefix convention such as `query:` and `passage:` | Good candidate, but adds prompt-format rules to document and enforce |
| `intfloat/e5-base-v2` | 768 | Strong retrieval-oriented model family | Larger and slower on CPU; also requires prefix convention | Better for later quality tuning, but heavier for first implementation |

## Selected Model

Selected model: **`sentence-transformers/all-MiniLM-L6-v2`**

Provider/repository: Hugging Face / Sentence Transformers

Model type: local dense embedding model

Embedding dimension: 384

## Reason for Selection

`sentence-transformers/all-MiniLM-L6-v2` was selected because it is lightweight, established, CPU-usable, reproducible by model name, and appropriate for primarily English Computer Engineering advising content. It avoids the complexity of query/document prefix conventions required by E5-style models while still supporting cosine-similarity semantic search.

The model is not the largest candidate, but that is intentional. The project is intended to run locally on a student laptop, and this stage prioritizes a reliable baseline embedding pipeline before vector database integration and retrieval tuning.

## Reproducibility

The model is loaded by name:

```text
sentence-transformers/all-MiniLM-L6-v2
```

The model may be downloaded from Hugging Face the first time the embedding script runs. Large model binaries should not be committed to Git.
