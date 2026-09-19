# WEX428 Comprehensive RAG Evaluation Report After Reliability Fixes

Generated at: `2026-09-18T20:35:59+00:00`

## Scope

This report summarizes the saved after-fix comprehensive RAG evaluation results. It uses the existing completed output in `docs/rag-comprehensive-evaluation-results-after-reliability-fixes.json`; no cases were regenerated for this report.

The evaluation covers the same 80-case set as the pre-fix baseline: 60 original representative questions from `ceng-questions.pdf` plus 20 paraphrased/unseen questions across major categories. This report is measurement-only and does not modify production retrieval, embeddings, the vector database, the LLM, prompts, thresholds, the knowledge base, evaluation questions, or rubric.

Answer-quality labels are an automated preliminary rubric based on retrieval relevance, answer status, and citation validation. They are useful for project evaluation, but they do not replace manual claim-level factual review.

## Completion Check

- Saved after-fix cases completed: 80/80
- Original questions completed: 60/60
- Paraphrased/unseen questions completed: 20/20
- Python evaluation process running at final inspection: no
- Action taken: finalized this Markdown report from saved results only

## After-Fix Summary

- Total cases: 80
- Original questions tested: 60
- Paraphrased/unseen questions tested: 20
- Answered cases with valid citations: 65/65
- Appropriate refusals: 6

## Before / After Comparison

| Metric | Pre-fix baseline | After reliability fixes | Change |
|---|---:|---:|---:|
| Completed cases | 80 | 80 | 0 |
| Original questions | 60 | 60 | 0 |
| Paraphrased/unseen questions | 20 | 20 | 0 |
| Answered cases | 57 | 65 | +8 |
| Answered cases with valid citations | 57/57 | 65/65 | +8 valid answered cases |
| Errors | 8 | 2 | -6 |
| Insufficient-information responses | 12 | 11 | -1 |
| Out-of-scope responses | 3 | 2 | -1 |
| Correct / well-supported | 32/80 (40.0%) | 61/80 (76.2%) | +29 cases, +36.2 pp |
| Correct or appropriate refusal | 38/80 (47.5%) | 67/80 (83.8%) | +29 cases, +36.2 pp |
| Partially correct / partially supported | 9/80 (11.2%) | 7/80 (8.8%) | -2 cases, -2.5 pp |
| Unsupported or incorrect | 33/80 (41.2%) | 6/80 (7.5%) | -27 cases, -33.8 pp |
| Highly relevant or relevant retrieval | 38/80 (47.5%) | 74/80 (92.5%) | +36 cases, +45.0 pp |
| Irrelevant retrieval | 41/80 (51.2%) | 4/80 (5.0%) | -37 cases, -46.2 pp |

## Retrieval Quality Results

| Label | Count |
|---|---:|
| Highly relevant | 29 |
| Irrelevant | 4 |
| Partially relevant | 2 |
| Relevant | 45 |

## Answer Status Results

| Label | Count |
|---|---:|
| answered | 65 |
| error | 2 |
| insufficient_information | 11 |
| out_of_scope | 2 |

## Answer-Quality Results

| Label | Count |
|---|---:|
| Appropriate refusal / insufficient information | 6 |
| Correct / well-supported | 61 |
| Partially correct / partially supported | 7 |
| Unsupported or incorrect | 6 |

## Weak Categories / Topics

- Choosing Computer Engineering over other engineering: 1 case - `q060`
- Choosing specialization focus: 1 case - `q038`
- Coding-only misconception: 1 case - `q056`
- Computer Engineering definition paraphrase: 1 case - `p001`
- Computer Engineering versus Computer Science: 1 case - `q005`
- Cybersecurity career paraphrase: 1 case - `p008`
- Cybersecurity specialist pathway: 1 case - `q035`
- Hackathons and competitions: 1 case - `q045`
- Master's degree necessity: 1 case - `q046`
- Master's versus industry paraphrase: 1 case - `p020`
- Specialization choice paraphrase: 1 case - `p017`
- Student CV: 1 case - `q043`
- Teamwork skills: 1 case - `q014`

## Representative Successful Examples

- `q001` (Computer Engineering definition): retrieval `Relevant`, answer `Correct / well-supported`.
- `q002` (Computer Engineering curriculum scope): retrieval `Relevant`, answer `Correct / well-supported`.
- `q003` (Choosing Computer Engineering): retrieval `Relevant`, answer `Correct / well-supported`.
- `q004` (Computer Engineering versus Software Engineering): retrieval `Relevant`, answer `Correct / well-supported`.
- `q006` (Hardware and software balance): retrieval `Relevant`, answer `Correct / well-supported`.

## Representative Failure / Caution Examples

- `q005` (Computer Engineering versus Computer Science): retrieval `Irrelevant`, answer `Unsupported or incorrect`. Note: Answered with valid citation format, but retrieved categories did not match expectations.
- `q014` (Teamwork skills): retrieval `Irrelevant`, answer `Unsupported or incorrect`. Note: Answered with valid citation format, but retrieved categories did not match expectations.
- `q035` (Cybersecurity specialist pathway): retrieval `Highly relevant`, answer `Partially correct / partially supported`. Note: Pipeline refused; manual review should decide whether available evidence should have supported an answer.
- `q038` (Choosing specialization focus): retrieval `Highly relevant`, answer `Partially correct / partially supported`. Note: Pipeline refused; manual review should decide whether available evidence should have supported an answer.
- `q043` (Student CV): retrieval `Relevant`, answer `Unsupported or incorrect`. Note: missing inline [S#] citation.
- `q045` (Hackathons and competitions): retrieval `Partially relevant`, answer `Partially correct / partially supported`. Note: Pipeline refused; manual review should decide whether available evidence should have supported an answer.
- `q046` (Master's degree necessity): retrieval `Relevant`, answer `Partially correct / partially supported`. Note: Pipeline refused; manual review should decide whether available evidence should have supported an answer.
- `q056` (Coding-only misconception): retrieval `Relevant`, answer `Partially correct / partially supported`. Note: Pipeline refused; manual review should decide whether available evidence should have supported an answer.

## Evaluation Limitations

- Automated citation validation confirms citation format and label availability, not full factual entailment.
- Some advisory questions legitimately require cautious or insufficient-information responses.
- Local LLM outputs may vary between runs.
- The evaluation records passage previews and sources, but final grading should manually review representative answers before defense.

## Files

- After-fix structured results: `docs/rag-comprehensive-evaluation-results-after-reliability-fixes.json`
- After-fix Markdown report: `docs/rag-comprehensive-evaluation-report-after-reliability-fixes.md`
- Pre-fix structured baseline: `docs/rag-comprehensive-evaluation-results.json`
- Pre-fix Markdown baseline: `docs/rag-comprehensive-evaluation-report.md`
- Case set: `tests/rag_comprehensive_evaluation_cases.json`
