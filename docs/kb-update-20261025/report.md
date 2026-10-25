# Knowledge-base update (2026-10-25)

Three sources changed, and no other sources were added. The TÜİK English note came from the list recommended after the spec fix. The other two recommended sources, the src_124 KARPİEM subpages and CyBOK OS security, were **not** added.

| Source | Change | Chunks before → after |
|---|---|---:|
| src_095 BLS Employment Projections, table 1.4 | Each table row is written out with its column headers and the table caption ([preprocess_sources.py](../../scripts/preprocess_sources.py) `TABLE_ROWS_WITH_HEADERS`). Before, the "Software developers" row was a line of numbers without column names. | 3 → 11 |
| src_122 OSTİM student communities | The list of 45 communities in 7 categories is extracted from the page's inline data (`var CATS` / `var COMM`). Before, the source was excluded from chunking because the HTML text held only the page frame. | 0 → 1 |
| src_132 (new) | Curated English note of src_103 (TÜİK Higher Education Employment Indicators 2025, as reported by Ekonomi Gazetesi). Every figure was checked against the Turkish text of src_103, which stays indexed. | 0 → 2 |

Totals: 2833 → 2844 chunks and 109 → 111 indexed sources. Preprocessing, chunking, embedding (`--reuse`: 2830 embeddings reused, 14 encoded) and the Chroma rebuild were run with the repository scripts. The chunk diff touches only these three sources. Backup of the previous index: `D:/ceng-backup-20261025-pre-kb-update`.

## Retrieval check

Paraphrase retrieval test (`scripts/evaluate_retrieval_paraphrases.py --options live`, 313 scored cases), live retriever before and after:

| Set | n | Recall@5 before → after | MRR@10 before → after |
|---|---:|---:|---:|
| Overall | 313 | 0.501 → 0.500 | 0.555 → 0.555 |
| Paraphrase | 220 | 0.409 → 0.407 | 0.536 → 0.537 |
| Unseen | 93 | 0.719 → 0.719 | 0.600 → 0.599 |
| Turkish sources | 68 | 0.440 → 0.440 | 0.416 → 0.413 |
| OSTİM-specific | 115 | 0.489 → 0.489 | 0.556 → 0.554 |

No case changes its hit@5. The test set has no case that expects the three changed sources, so it only shows that nothing else got worse. A direct check of the questions behind the change, top 5 of the live retriever:

- "Can I find a job after graduation?" → src_132_chunk_002 at rank 1, src_103 at ranks 3 and 5, and src_095 at rank 4.
- "What student clubs are there at OSTIM Technical University?" → src_122_chunk_001 at rank 1.
- "What is the projected job growth for software developers?" → src_095 chunks 003 and 007 at ranks 4 and 5.
- "How long does it take ICT graduates in Turkey to find a job?" → src_132_chunk_002 at rank 1.

Files: [retrieval-paraphrases-before.json](retrieval-paraphrases-before.json) and [retrieval-paraphrases-after.json](retrieval-paraphrases-after.json).
