# Full 200-Question CENG AI Advisor Evaluation

Generated at: `2026-10-13T16:12:22+00:00`
Complete: `True`
Dataset: `docs\semantic-coverage-200-questions.json`

## Procedure

Official 200-question semantic coverage dataset; current backend query-resolution/session logic; current RAGPipeline, KB, Chroma collection, and Ollama model; evaluation-only scoring with citation-label validity and claim/evidence lexical support checks.

The scoring is stricter than citation-format checking: answered cases require valid citation labels, no built-in unsupported-generation warning, expected-topic evidence, and a lexical claim/evidence support check. It remains an automated evaluation and should not be represented as human proof of every factual claim.

## Aggregate Results

- correct_evidence_supported: 2/200 (1.0%)
- correct_insufficient_information: 35/200 (17.5%)
- incorrect_refusal_evidence_exists: 40/200 (20.0%)
- unsupported_incorrect_or_misleading: 123/200 (61.5%)
- runtime_error: 0/200 (0.0%)
- Answered cases with valid citation labels: 125/125 (100.0%)
- Answered cases passing evidence-support checks: 2/125 (1.6%)
- Mean latency: 35.56s

## Results By Student-Question Category

| Category | Total | Supported | Correct insuff. | Incorrect refusal | Unsupported/misleading | Runtime errors |
|---|---:|---:|---:|---:|---:|---:|
| ai_future | 14 | 0 | 0 | 2 | 12 | 0 |
| career_employment | 28 | 1 | 3 | 6 | 18 | 0 |
| complex | 12 | 0 | 1 | 7 | 4 | 0 |
| curriculum | 14 | 0 | 0 | 3 | 11 | 0 |
| cybersecurity | 12 | 1 | 0 | 4 | 7 | 0 |
| fundamentals | 12 | 0 | 0 | 0 | 12 | 0 |
| hardware_networks | 12 | 0 | 0 | 2 | 10 | 0 |
| mathematics | 12 | 0 | 0 | 2 | 10 | 0 |
| multi_turn | 22 | 0 | 2 | 5 | 15 | 0 |
| out_of_scope | 13 | 0 | 13 | 0 | 0 | 0 |
| programming_software | 18 | 0 | 0 | 5 | 13 | 0 |
| student_local | 18 | 0 | 3 | 4 | 11 | 0 |
| unsupported | 13 | 0 | 13 | 0 | 0 | 0 |

## Most Common Systematic Failures

- 121: answered_with_uncited_claims
- 24: false_refusal: unsupported claim could not be matched to retrieved evidence
- 2: false_refusal: standalone_domain_question
- 2: false_refusal: answer appears incomplete or truncated
- 2: false_refusal: retrieved evidence does not compare the requested learning order or prerequisites
- 2: false_refusal: missing inline [S#] citation
- 2: false_refusal: missing inline [S#] citation on one or more answer paragraphs or bullets
- 1: false_refusal: citation labels are not in retrieved context: ['S7']
- 1: false_refusal: retrieved evidence does not directly rate command-line or terminal-skill importance for Computer Engineering
- 1: false_refusal: retrieved evidence does not address the requested learning alternatives
- 1: answered_without_relevant_expected_evidence
- 1: cited_passages_do_not_support_claim_terms

## Files

- Structured results: `results.json`
- Report: `report.md`
