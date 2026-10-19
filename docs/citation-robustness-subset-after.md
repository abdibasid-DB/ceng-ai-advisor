# WEX428 Comprehensive RAG Evaluation Report

Generated at: `2026-10-07T17:06:29+00:00`

## Scope

This evaluation runs the existing local RAG pipeline against all 60 representative questions from `ceng-questions.pdf` plus paraphrased/unseen questions across major categories. It does not modify production retrieval, embeddings, the vector database, the LLM, or prompts.

Answer-quality labels are an automated preliminary rubric based on retrieval relevance, answer status, and citation validation. They are useful for project evaluation, but they do not replace manual claim-level factual review.

## Summary

- Total cases: 6
- Original questions tested: 5
- Paraphrased/unseen questions tested: 1
- Answered cases with valid citations: 4/4
- Appropriate refusals: 1

## Retrieval Quality Results

| Label | Count |
|---|---:|
| Highly relevant | 2 |
| Irrelevant | 1 |
| Relevant | 3 |

## Answer Status Results

| Label | Count |
|---|---:|
| answered | 4 |
| error | 1 |
| insufficient_information | 1 |

## Answer-Quality Results

| Label | Count |
|---|---:|
| Appropriate refusal / insufficient information | 1 |
| Correct / well-supported | 3 |
| Unsupported or incorrect | 2 |

## Weak Categories / Topics

- Future-proof career concern: 1 case(s) - q027
- Student CV: 1 case(s) - q043

## Representative Successful Examples

- `q002` (Computer Engineering curriculum scope): retrieval `Highly relevant`, answer `Correct / well-supported`.
- `q015` (Student skills development): retrieval `Relevant`, answer `Correct / well-supported`.
- `p002` (OSTIM Computer Engineering curriculum paraphrase): retrieval `Highly relevant`, answer `Correct / well-supported`.

## Representative Failure / Caution Examples

- `q027` (Future-proof career concern): retrieval `Relevant`, answer `Unsupported or incorrect`. Note: unsupported claim could not be matched to retrieved evidence
- `q043` (Student CV): retrieval `Irrelevant`, answer `Unsupported or incorrect`. Note: Answered with valid citation format, but retrieved categories did not match expectations.

## Evaluation Limitations

- Automated citation validation confirms citation format and label availability, not full factual entailment.
- Some advisory questions legitimately require cautious or insufficient-information responses.
- Local LLM outputs may vary between runs.
- The evaluation records passage previews and sources, but final grading should manually review representative answers before defense.

## Files

- Structured results: `C:/Users/HP/OneDrive/Documents/ChatGPT/ceng-ai-advisor/docs/rag-comprehensive-evaluation-results.json`
- Case set: `C:/Users/HP/OneDrive/Documents/ChatGPT/ceng-ai-advisor/tests/rag_comprehensive_evaluation_cases.json`
