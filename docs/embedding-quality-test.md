# Stage 11 - Embedding Quality Test

## Test Setup

The local embedding matrix was generated from `knowledge_base/chunks/chunks.jsonl` using:

- Model: `sentence-transformers/all-MiniLM-L6-v2`
- Embedding dimension: 384
- Embeddings: normalized
- Similarity metric: cosine similarity
- Top-K inspected: 5

The test utility embeds each query locally, compares it against `knowledge_base/embeddings/embeddings.npy`, and reports the highest-scoring chunks. This is a validation utility only; it is not a vector database, production retriever, RAG pipeline, or chatbot.

## Representative Queries

| Query | Top result | Qualitative finding |
|---|---|---|
| What programming languages should a Computer Engineering student learn? | `src_039_chunk_004` | Relevant. Results included programming course guidance, OSTIM object-oriented programming course content, and developer ecosystem language evidence. |
| What courses are taught in Computer Engineering? | `src_039_chunk_001` | Partially relevant. The query retrieved course-related content, but Brown introductory course guidance ranked above OSTIM curriculum chunks. This suggests future vector-database retrieval may need metadata/category filtering or source-priority boosting for university-specific curriculum questions. |
| Can Computer Engineers work in cybersecurity? | `src_017_chunk_119` | Partially relevant. Results included computing occupations, skills, and security-management references, but direct cybersecurity-specialization evidence was weaker than desired. This category may need stronger dedicated cybersecurity sources or metadata-assisted retrieval later. |
| What career opportunities are available after graduation? | `src_036_chunk_005` | Relevant but broad. Results included career exploration, skills-first labor-market pathways, portfolios, future job roles, and graduate-study preparation. |
| How is artificial intelligence affecting computing jobs? | `src_017_chunk_005` | Highly relevant. Top results came from WEF and OECD chunks about technological change, AI skills, job transformation, reskilling, and AI-related roles. |
| Are internships important for students? | `src_018_chunk_001` | Highly relevant. Top results included NACE internship evidence, internship hiring, OSTIM course/project context, and career-preparation sources. |

## Retrieval-Quality Concerns

- Curriculum queries may need source-priority handling so official OSTIM curriculum chunks rank above general university course-advice pages.
- Cybersecurity queries need stronger directly relevant evidence in later source expansion or careful metadata filtering.
- Large report chunks can dominate broad career/future-technology queries because they provide many semantically rich chunks.
- This test is qualitative only. No ground-truth relevance labels have been created yet, so no quantitative accuracy score is claimed.

## Validation Result

The embedding quality is sufficient for the next stage, where vector database integration and retrieval configuration can be designed and tested. The noted ranking issues should be revisited during retrieval evaluation.
