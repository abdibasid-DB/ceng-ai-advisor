# Stage 12 - ChromaDB Vector Store Report

## Purpose

A vector database stores text chunks together with their embedding vectors so semantically similar user questions can retrieve relevant source passages. This stage creates a local persistent ChromaDB database for the already-generated Stage 11 embeddings.

This stage does not implement Ollama, a generative LLM, RAG prompt construction, final retrieval optimization, chatbot behavior, API endpoints, or frontend features.

## ChromaDB Selection

ChromaDB was selected because it is a local vector database that can persist embeddings and metadata on disk. It fits the university project requirement for a local RAG architecture and avoids hosted vector databases such as Pinecone, Weaviate Cloud, Qdrant Cloud, or Elasticsearch Cloud.

## Vector Store Design

| Field | Value |
|---|---|
| Database type | ChromaDB |
| ChromaDB version | 1.5.9 |
| Persistence path | `knowledge_base/vector_store/chroma/` |
| Collection name | `ceng_advisor_chunks` |
| Distance metric | Cosine distance |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` |
| Embedding dimension | 384 |
| Expected records | 792 |
| Indexed records | 792 |

The generated Chroma database files are local reproducible artifacts and are ignored by `.gitignore`. The manifest is kept separately at `knowledge_base/vector_store/vector_store_manifest.json`.

## Stored Record Structure

Each Chroma record uses:

- ID: `chunk_id`
- Document: chunk text
- Embedding: existing 384-dimensional embedding from `knowledge_base/embeddings/embeddings.npy`
- Metadata: retrieval-safe chunk/source metadata

Metadata fields stored:

- `source_id`
- `chunk_index`
- `title`
- `source_name`
- `source_type`
- `url`
- `publication_date`
- `category`
- `language`
- `processed_file_path`
- `section_heading`
- `word_count`
- `character_count`

Null metadata values are converted to empty strings for Chroma compatibility. No metadata is invented.

## Rebuild Behavior

The rebuild strategy is deterministic:

1. Delete and recreate `knowledge_base/vector_store/chroma/`.
2. Load the existing chunks, embeddings, and embedding metadata.
3. Validate counts, dimensions, chunk IDs, source IDs, and numeric embedding integrity.
4. Create the collection `ceng_advisor_chunks`.
5. Add all records with deterministic `chunk_id` values.

This prevents duplicate records when the build script is rerun.

## Score Interpretation

The collection uses Chroma cosine distance via:

```python
metadata={"hnsw:space": "cosine"}
```

For Chroma cosine distance:

- Lower distance means more similar.
- With normalized embeddings, cosine similarity can be interpreted as:

```text
cosine_similarity = 1 - distance
```

The test script reports both `distance` and converted `cosine_similarity` to avoid confusing the two.

## Integrity Validation

Validation confirmed:

- Collection exists.
- Collection count is 792.
- Persistent reload count is 792.
- Chunk count is 792.
- Embedding count is 792.
- Embedding dimension is 384.
- Embedding metadata order matches deterministic chunk order.
- Duplicate chunk IDs: 0.
- NaN values: 0.
- Infinite values: 0.
- Every chunk maps to an approved source ID.
- Sample metadata is readable.
- Sample document text is present.
- Top-K queries work after reopening the persistent database.
- No Ollama, RAG, chatbot, or frontend/backend AI feature was created.

## Representative Top-K Findings

| Query area | Finding |
|---|---|
| Department/curriculum | Partially relevant. General Brown CS course-advice chunks ranked above OSTIM curriculum chunks, although OSTIM `src_004` chunks appeared in the Top-5. |
| Programming | Relevant. Results included programming-course guidance, OSTIM course content, and developer ecosystem programming-language evidence. |
| Careers | Relevant. Results included O*NET computer hardware engineer evidence, WEF future-jobs material, and Linux Foundation tech talent evidence. |
| Artificial Intelligence | Highly relevant. Results included WEF AI/job transformation chunks and Google research on generative AI and development work. |
| Cybersecurity | Partially relevant. Results included broad security-management and computing occupation evidence, but direct cybersecurity-specialization evidence remains weak. |
| Internships | Relevant. NACE internship evidence ranked first, with OSTIM curriculum/project context and internship hiring evidence also retrieved. |

## Stage 11 Comparison

ChromaDB results are consistent with the Stage 11 direct cosine-similarity tests. The scores match the expected conversion from Chroma cosine distance to cosine similarity.

No large unexplained differences were observed, which supports that:

- Embedding order was preserved.
- Embeddings were inserted correctly.
- The collection metric is correctly configured.
- Chunk/source metadata is readable after persistence reload.

## Known Retrieval Weaknesses

Curriculum:

General course-advice chunks still outrank some OSTIM-specific curriculum chunks for broad curriculum questions. This should be addressed later with metadata/category-aware retrieval or source-priority logic, not by hard-coding individual source IDs.

Cybersecurity:

Cybersecurity retrieval remains only partially relevant. The current knowledge base contains some security-related career/skills evidence, but later source expansion or retrieval filtering may be needed for stronger cybersecurity advising.

## Source Traceability

Retrieved records preserve:

`user query` -> `query embedding` -> `ChromaDB result` -> `chunk_id` -> `source_id` -> `url`

This is sufficient for later RAG and frontend source/context display.

## Commands

Rebuild the vector store:

```powershell
python scripts\build_vector_store.py
```

Run representative Top-K tests:

```powershell
python scripts\test_vector_store.py --preset-stage12 --top-k 5
```

Run one custom test query:

```powershell
python scripts\test_vector_store.py "What courses are taught in Computer Engineering?" --top-k 5
```

## Limitations

- This is not the final retrieval pipeline.
- No metadata/category-aware retrieval optimization has been implemented yet.
- No chatbot answers are generated.
- ChromaDB database files are generated artifacts and should be rebuilt when chunks or embeddings change.

## Readiness Decision

**A. VECTOR DATABASE READY FOR RETRIEVAL PIPELINE**
