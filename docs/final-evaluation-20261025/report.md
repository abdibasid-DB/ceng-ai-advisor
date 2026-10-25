# Final evaluation of the frozen system (2026-10-25)

**System:** commit 6426e67, with:
- the spec-question fixes of 208e21d;
- temperature 0, seed 42 and the prompt-cache reset (87507ae, [decision](../temperature-seed-20261025/report.md));
- the knowledge-base update to 2844 chunks from 111 sources ([report](../kb-update-20261025/report.md));
- `qwen2.5:3b` through Ollama 0.40.10, run with `LLAMA_ARG_CACHE_RAM=0`; the server log says "prompt cache is disabled".

The runner is [run_final.py](run_final.py). It runs the same steps and backend path as [the Oct 23 run](../final-evaluation-20261023/run_final.py), without the manual-check step. The log is in [run.log](run.log). No runtime errors occurred.

## 200 questions

| Label | Count |
|---|---:|
| Supported by evidence | 95 (47.5%) |
| Correct refusal | 32 (16.0%) |
| Incorrect refusal (evidence exists) | 46 (23.0%) |
| Unsupported, incorrect or misleading | 27 (13.5%) |
| Runtime errors | 0 |

- 122 answered, all with valid citation labels; 95 of them (77.9%) pass the evidence-support checks.
- Mean latency: 35.15 s per answer. Mean wall time: 36.3 s per case, including multi-turn setup turns.
- All 13 out-of-scope and all 13 unsupported questions were refused.

[full200-report.md](full200-report.md), [full200-results.json](full200-results.json)

## Comparison with Oct 18 and Oct 23

The full category tables, the same-case-ID tables and the 53 label changes are in [comparison.md](comparison.md). All runs are labelled again with the current classifier. Totals:

| Run | n | Supported | Correct refusal | Incorrect refusal | Unsupported | Mean s/case |
|---|---:|---:|---:|---:|---:|---:|
| Oct 18 | 193 | 92 | 34 | 50 | 17 | 26.7 |
| Oct 23 | 200 | 96 | 33 | 43 | 28 | 29.7 |
| **Oct 25** | 200 | **95** | 32 | 46 | 27 | 36.3 |
| Oct 23, same 193 IDs | 193 | 92 | 33 | 41 | 27 | 28.2 |
| **Oct 25, same 193 IDs** | 193 | **94** | 32 | 43 | 24 | 35.0 |

- Overall the Oct 25 run is level with Oct 23: 95 vs 96 supported, and 27 vs 28 unsupported.
- **Better:**
  - curriculum: 9 → 11 supported, 2 → 0 unsupported;
  - mathematics: 5 → 8;
  - hardware_networks: 7 → 9;
  - the OSTİM club questions S127/S128, now answered from src_122.
- **Worse:**
  - complex: 7 → 4;
  - multi_turn: 11 → 8;
  - career_employment: 12 → 10;
  - fundamentals: 10 → 8.
- 53 of 200 labels changed between Oct 23 (temperature 0.2, no seed) and Oct 25. A single unseeded run is noisy at that scale, so differences of one to three cases per category are not significant.
- Answers are slower: 36.3 vs 29.7 s per case. The prompt cache is off and there is a one-token reset before each generation, so every prompt is evaluated from the start.

## 60 ceng-questions

| | Oct 23 | Oct 25 |
|---|---:|---:|
| Answered | 43 | 37 |
| Insufficient information | 17 | 23 |
| Correct / well-supported | 42 | 34 |
| Partially correct / partially supported | 9 | 11 |
| Appropriate refusal | 8 | 12 |
| Unsupported or incorrect | 1 | 3 |
| Answered with valid citations | 43 of 43 | 37 of 37 |
| Retrieval highly relevant / relevant / irrelevant | 47 / 8 / 5 | 47 / 8 / 5 |
| Mean s/question | 27.0 | 35.3 |

Retrieval quality is unchanged, but the model answers 6 fewer of these questions. [ceng60-report.md](ceng60-report.md)

## Specification questions

| Case | Oct 23 | Oct 25 | Assessment of the Oct 25 answer |
|---|---|---|---|
| SPEC1 Will AI replace computer engineers? | refused | refused | — |
| SPEC2 Is Computer Engineering still worth studying? | refused | answered | 1 of 4 sentences supported (O*NET outlook). "Jobs in Computer Engineering are not at high risk of automation" is not in the OECD passage. |
| SPEC3 Can I find a job after graduation? | answered | answered | One sentence, cited to src_132: "the average time to first job … is relatively short". The passage gives 14.2 months and makes no comparison, so "relatively short" is unsupported. |
| SPEC4 Not good at maths, can I still succeed? | refused | answered | 2 of 3 sentences supported. The only maths sentence is "the quantity and level of mathematics … are decided by each program". |

SPEC1, SPEC2 and SPEC4 give answers identical to the three temperature-0 runs of 2026-10-23, on the index before the update. SPEC3 changed because src_132 is now retrieved. [spec4-report.md](spec4-report.md)

## NLI faithfulness (evaluation only)

`cross-encoder/nli-deberta-v3-small`, cited sentence vs cited passages; a sentence counts as entailed at ≥ 0.5. [nli-faithfulness.json](nli-faithfulness.json), [nli-rows.json](nli-rows.json)

| Set | Answers scored | Cited sentences | Sentences entailed (Oct 23 → 25) | Answers fully entailed (Oct 23 → 25) | Mean answer faithfulness (Oct 23 → 25) |
|---|---:|---:|---:|---:|---:|
| 200 questions | 121 | 256 | 49.5% → 50.0% | 34.1% → 38.0% | 0.534 → 0.552 |
| 60 questions | 37 | 89 | 40.6% → 44.9% | 18.6% → 21.6% | 0.409 → 0.449 |
| Spec questions | 3 | 8 | 33.3% → 37.5% | 0.0% → 0.0% | 0.333 → 0.306 |
| **All** | 161 | 353 | 46.9% → 48.4% | 29.9% → 33.5% | 0.501 → 0.524 |

## Reproducibility check

The 10 demo questions ([../demo-questions.md](../demo-questions.md)) were run a second time through the same path. All 10 answers, retrieved sources and the follow-up setup answer were identical. [demo-check-results.json](demo-check-results.json)
