# Applying retrieval option f (2026-10-22)

Option f from the Step 1.2 experiment ([summary](../retrieval-paraphrases-step-1-2/summary.md)) is now the live retrieval setup:

- **Chunking:** ~180-word chunks (maximum 220, overlap 40) after cleaning (source-id headers, page numbers, cookie banners, shared HTML navigation, repeated HTML paragraphs). `scripts/chunk_documents.py` gives 2822 chunks from all 103 chunk-eligible documents. The old setup had 1132 chunks of 380/500/60 words.
- **Embeddings:** `BAAI/bge-m3` dense vectors, 1024 dimensions, `max_seq_length` 512.
  - The experiment's option-e embeddings were reused (`scripts/generate_embeddings.py --reuse`) because chunk IDs and texts matched exactly.
  - Three chunks re-encoded with bge-m3 had cosine 1.0 with the stored vectors.
- **Hybrid search:** BM25 (`rank_bm25.BM25Okapi`, case- and diacritic-folded word tokens) fused with the reranked vector candidates by reciprocal rank fusion (k = 60, 12 BM25 candidates), as in option f (`backend/app/rag/retriever.py`).
  - **One difference from the experiment:** BM25-only hits from the live excluded sources are dropped, as they already are on the vector side.
- **Backup** of the previous index, chunks, embeddings and config: `D:/ceng-backup-20261022-pre-option-f`.

## Check that the live retriever reproduces option f

The live retriever was run on all 313 scored Step 1.2 cases:
- 309 of 313 top-10 lists are identical to option f.
- Recall@5 is 0.513 (option f: 0.514). MRR@10 (0.578) and Hit@5 (0.760) are identical.
- Mean retrieval time is 0.151 s/query (the query-encoder model was already loaded).

## MIN_SIMILARITY_THRESHOLD: 0.30 → 0.50

Script: `scripts/calibrate_retrieval_threshold.py`. Per-question data: `retrieval-threshold.json`.

The gate refuses a question when the top chunk's cosine similarity, or the second-best of the top 5, is below the threshold. bge-m3 gives even unrelated text a cosine score of about 0.4–0.55, so MiniLM's 0.30 would block nothing.

**Test questions:**
- **In scope (528, deduplicated):**
  - full-200 questions with `answer_or_gap`, excluding multi-turn follow-ups
  - the 240 paraphrases
  - unseen-coverage `answer` cases
  - the in-scope retrieval and RAG test cases
  - comprehensive-evaluation `answer` cases
- **Out of scope or insufficient (39):**
  - full-200 `out_of_scope`/`insufficient`
  - unseen-coverage `insufficient`
  - retrieval and RAG test out-of-scope cases
  - the unsupported in-domain RAG case

| Threshold | In-scope pass | Refuse set blocked by the gate |
|---:|---:|---:|
| previous (MiniLM, 0.30) | 98.3% | 16/39 |
| 0.45 | 99.6% | 7/39 |
| 0.48 | 98.7% | 11/39 |
| **0.50** | **96.8%** | **14/39** |
| 0.51 | 95.6% | 15/39 |
| 0.52 | 93.8% | 15/39 |

**Rule:** at least 95% of in-scope questions must pass, and out-of-scope/insufficient questions must be refused at least as often as before.

- **At the gate alone, no threshold meets both parts.** At every threshold that passes 95% of in-scope questions, the gate blocks 15 or fewer refuse-set questions, against 16 before.
- **End-to-end, the rule holds.** The pre-retrieval query classifier (`query_understanding`, kind `out_of_scope_persona_meta`) sends 20 of the 39 straight to the out-of-scope reply. That covers every question the old gate blocked.
- **The result is the same at every candidate threshold.** With the classifier and gate together, 20/39 are blocked before the LLM, the same as before.
- **The other 19 are in-domain questions** about exact fees, guarantees, private data and similar topics. The gate never blocked them with either model. They rely on the prompt and the grounding checks, as before.

**Choice: 0.50.** It meets the 95% rule with some margin (96.8%, against 95.6% at 0.51). 0.51 would add one more gate block, but that question is already handled end-to-end.

## Grounding thresholds

**Method:**
- Script: `scripts/evaluate_semantic_thresholds.py --model ...`, replaying the 2026-10-18 full-200 answers.
- Per-case data: `grounding-all-MiniLM-L6-v2.json` and `grounding-bge-m3.json`.
- Rule: the lowest bge-m3 threshold that accepts no more mismatched pairs and no more known-unsupported answers or claims than MiniLM did at its old threshold.

| Check | MiniLM at old threshold | bge-m3 at new threshold |
|---|---|---|
| question ↔ answer (rescue of the topic-term check) | 0.65: 45/90 correct, 6/19 unsupported, 2/545 mismatched | **0.70**: 40/90 correct, 5/19 unsupported, 1/545 mismatched |
| cited sentence ↔ passage sentence | 0.70: 110/202 correct, 0/7 flagged, 5/189 mismatched | **0.72**: 139/202 correct, 0/7 flagged, 5/189 mismatched |

bge-m3 at 0.68 or 0.69 for question ↔ answer would accept 4 mismatched pairs, so the threshold stops at 0.70. For sentence ↔ passage, 0.72 accepts 29 more correct claims with no more false acceptances.

## DEFAULT_TOP_K: kept at 5

Option f ranking, Step 1.2 cases:

| k | 3 | 4 | 5 | 6 | 8 | 10 |
|---|---:|---:|---:|---:|---:|---:|
| Recall@k | 0.406 | 0.463 | 0.514 | 0.543 | 0.581 | 0.619 |

**Why k stays at 5:**
- The prompt takes passages until 3,000 characters are used, at no more than 700 characters per passage.
- In the 2026-10-18 run, 95 of 153 LLM prompts held 4 passages and 32 held 5.
- New chunks average 1,308 characters, so they are still cut to 700 characters. The prompt therefore fits about the same 4–5 passages.
- A larger k would only add passages that never reach the model, unless the context budget were raised. Raising it would add CPU generation time on every answer.
