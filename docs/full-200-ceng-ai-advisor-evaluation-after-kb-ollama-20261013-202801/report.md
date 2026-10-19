# Full 200-Question CENG AI Advisor Evaluation

Generated at: `2026-10-16T13:38:12+00:00`
Complete: `True`
Dataset: `docs\semantic-coverage-200-questions.json`

## Procedure

Official 200-question semantic coverage dataset; current backend query-resolution/session logic; current RAGPipeline, KB, Chroma collection, and Ollama model; evaluation-only scoring with citation-label validity and claim/evidence lexical support checks.

The scoring is stricter than citation-format checking: answered cases require valid citation labels, no built-in unsupported-generation warning, expected-topic evidence, and a lexical claim/evidence support check. It remains an automated evaluation and should not be represented as human proof of every factual claim.

## Aggregate Results

- correct_evidence_supported: 1/200 (0.5%)
- correct_insufficient_information: 34/200 (17.0%)
- incorrect_refusal_evidence_exists: 55/200 (27.5%)
- unsupported_incorrect_or_misleading: 106/200 (53.0%)
- runtime_error: 4/200 (2.0%)
- Answered cases with valid citation labels: 107/107 (100.0%)
- Answered cases passing evidence-support checks: 1/107 (0.9%)
- Mean latency: 63.24s

## Results By Student-Question Category

| Category | Total | Supported | Correct insuff. | Incorrect refusal | Unsupported/misleading | Runtime errors |
|---|---:|---:|---:|---:|---:|---:|
| ai_future | 14 | 0 | 0 | 4 | 9 | 1 |
| career_employment | 28 | 1 | 2 | 7 | 18 | 0 |
| complex | 12 | 0 | 1 | 4 | 7 | 0 |
| curriculum | 14 | 0 | 0 | 5 | 9 | 0 |
| cybersecurity | 12 | 0 | 0 | 5 | 7 | 0 |
| fundamentals | 12 | 0 | 0 | 2 | 9 | 1 |
| hardware_networks | 12 | 0 | 0 | 3 | 9 | 0 |
| mathematics | 12 | 0 | 0 | 4 | 8 | 0 |
| multi_turn | 22 | 0 | 2 | 8 | 10 | 2 |
| out_of_scope | 13 | 0 | 13 | 0 | 0 | 0 |
| programming_software | 18 | 0 | 0 | 7 | 11 | 0 |
| student_local | 18 | 0 | 3 | 6 | 9 | 0 |
| unsupported | 13 | 0 | 13 | 0 | 0 | 0 |

## Most Common Systematic Failures

- 106: answered_with_uncited_claims
- 32: false_refusal: unsupported claim could not be matched to retrieved evidence
- 6: false_refusal: standalone_domain_question
- 6: false_refusal: missing inline [S#] citation on one or more answer paragraphs or bullets
- 4: runtime_error: Local LLM failed: Ollama request timed out after 120 seconds.
- 2: false_refusal: unsupported claim could not be matched to retrieved evidence Local LLM citation retry failed: Ollama request timed out after 120 seconds.
- 2: false_refusal: retrieved evidence does not compare the requested learning order or prerequisites
- 2: false_refusal: missing inline [S#] citation
- 2: false_refusal: answer appears incomplete or truncated
- 1: false_refusal: retrieved evidence does not address the requested learning alternatives
- 1: false_refusal: retrieved evidence does not directly address hackathons or student coding competitions
- 1: false_refusal: retrieved evidence has too little overlap with the question terms: ['exams', 'explains', 'grading', 'official', 'regulation']

## Files

- Structured results: `results.json`
- Report: `report.md`
