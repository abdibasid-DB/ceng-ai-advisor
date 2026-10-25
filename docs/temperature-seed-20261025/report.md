# Temperature and seed decision (2026-10-25)

Question: should generation use temperature 0.2 with seed 42, or temperature 0 with seed 42?

Rule set before the runs: use 0.2 + seed 42 if it is reproducible **and** not worse than 0.2 without a seed (the 208e21d run). Otherwise keep 0 + seed 42.

**Decision: keep temperature 0 + seed 42** (`LLM_TEMPERATURE=0`, `LLM_SEED=42`, the defaults in [llm_config.py](../../backend/app/core/llm_config.py)). 0.2 + seed 42 is reproducible, but it is worse than 0.2 without a seed: 66 vs 75 supported out of 158.

All runs use the same code, the same index (2833 chunks, before the 2026-10-25 knowledge-base update) and [run_spec_fix.py](../spec-fix-20261023/run_spec_fix.py). Labels come from [compare.py](../spec-fix-20261023/compare.py), using the current official classifier. The seeded runs were made with the Ollama prompt cache switched off (`LLAMA_ARG_CACHE_RAM=0`, confirmed in the server log as "prompt cache is disabled").

## Reproducibility: the four spec questions

| Setting | Runs | Identical answers and sources | SPEC1 | SPEC2 | SPEC3 | SPEC4 |
|---|---:|---|---|---|---|---|
| 0 + seed 42 | 3 (`spec4-nc1..3`) | yes, 4/4 | refused | answered | answered | answered |
| 0.2 + seed 42 | 2 (`spec4-s02-r1/r2`) | yes, 4/4 | answered | refused | answered | refused |
| 0.2, no seed (208e21d) | — | no: SPEC1/SPEC2 changed between runs | | | | |

## 158 cases (138 cases of the 200-question set + 20 paraphrases)

| Setting | Supported | Correct refusal | Incorrect refusal | Unsupported | Mean s/case |
|---|---:|---:|---:|---:|---:|
| 0.2, no seed (`cases-after`, 208e21d) | 75 | 33 | 28 | 22 | 30.8 |
| 0 + seed 42 (`cases-t0`) | 66 | 32 | 33 | 27 | 37.0 |
| 0.2 + seed 42 (`cases-s02`) | 66 | 32 | 35 | 25 | 37.5 |

Per-category tables and case-by-case changes: [results/comparison-s02-vs-after.md](results/comparison-s02-vs-after.md), [results/comparison-s02-vs-t0.md](results/comparison-s02-vs-t0.md) and [results/comparison-t0.md](results/comparison-t0.md).

## Interpretation

- Both seeded settings give the same number of supported answers (66). 0.2 + seed has two fewer unsupported answers and two more incorrect refusals. On the spec questions, 0 + seed answers three of the four and 0.2 + seed answers two.
- The 75 of the unseeded run is a single sample, and that setting is not reproducible: 29 to 39 of the 158 labels change between any two of these runs. Each gap of about 9 cases therefore sits within run-to-run variance rather than showing that seeding makes answers worse. The rule above still decides against 0.2 + seed.
- The mean time per case is higher in the seeded runs (37 vs 31 s) because of the one-token prompt-cache reset before each generation and because the prompt cache is off: every prompt is evaluated from the start.
