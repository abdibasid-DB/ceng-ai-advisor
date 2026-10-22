# WEX428 Comprehensive RAG Evaluation Report

Generated at: `2026-10-22T21:00:38+00:00`

## Scope

This evaluation runs the existing local RAG pipeline against all 60 representative questions from `ceng-questions.pdf` plus paraphrased/unseen questions across major categories. It does not modify production retrieval, embeddings, the vector database, the LLM, or prompts.

Answer-quality labels are an automated preliminary rubric based on retrieval relevance, answer status, and citation validation. They are useful for project evaluation, but they do not replace manual claim-level factual review.

## Summary

- Total cases: 60
- Original questions tested: 60
- Paraphrased/unseen questions tested: 0
- Answered cases with valid citations: 43/43
- Appropriate refusals: 8

## Retrieval Quality Results

| Label | Count |
|---|---:|
| Highly relevant | 47 |
| Irrelevant | 5 |
| Relevant | 8 |

## Answer Status Results

| Label | Count |
|---|---:|
| answered | 43 |
| insufficient_information | 17 |

## Answer-Quality Results

| Label | Count |
|---|---:|
| Appropriate refusal / insufficient information | 8 |
| Correct / well-supported | 42 |
| Partially correct / partially supported | 9 |
| Unsupported or incorrect | 1 |

## Weak Categories / Topics

- AI work without master's: 1 case(s) - q047
- Choosing Computer Engineering: 1 case(s) - q003
- Choosing Computer Engineering over other engineering: 1 case(s) - q060
- Choosing specialization focus: 1 case(s) - q038
- Computer Engineering definition: 1 case(s) - q001
- Finding first internship: 1 case(s) - q042
- Hackathons and competitions: 1 case(s) - q045
- Master's degree necessity: 1 case(s) - q046
- Mathematics requirements: 1 case(s) - q010
- Student workload: 1 case(s) - q013
- Succeeding without coding background: 1 case(s) - q012
- Technologies before graduation: 1 case(s) - q037

## Representative Successful Examples

- `q002` (Computer Engineering curriculum scope): retrieval `Highly relevant`, answer `Correct / well-supported`.
- `q004` (Computer Engineering versus Software Engineering): retrieval `Relevant`, answer `Correct / well-supported`.
- `q005` (Computer Engineering versus Computer Science): retrieval `Relevant`, answer `Correct / well-supported`.
- `q006` (Hardware and software balance): retrieval `Highly relevant`, answer `Correct / well-supported`.
- `q007` (Student projects): retrieval `Highly relevant`, answer `Correct / well-supported`.

## Representative Failure / Caution Examples

- `q001` (Computer Engineering definition): retrieval `Irrelevant`, answer `Unsupported or incorrect`. Note: Answered with valid citation format, but retrieved categories did not match expectations.
- `q003` (Choosing Computer Engineering): retrieval `Irrelevant`, answer `Appropriate refusal / insufficient information`. Note: Pipeline refused because retrieved evidence was insufficient.
- `q010` (Mathematics requirements): retrieval `Highly relevant`, answer `Partially correct / partially supported`. Note: Pipeline refused; manual review should decide whether available evidence should have supported an answer.
- `q012` (Succeeding without coding background): retrieval `Highly relevant`, answer `Partially correct / partially supported`. Note: Pipeline refused; manual review should decide whether available evidence should have supported an answer.
- `q013` (Student workload): retrieval `Irrelevant`, answer `Appropriate refusal / insufficient information`. Note: Pipeline refused because retrieved evidence was insufficient.
- `q037` (Technologies before graduation): retrieval `Highly relevant`, answer `Partially correct / partially supported`. Note: Pipeline refused; manual review should decide whether available evidence should have supported an answer.
- `q038` (Choosing specialization focus): retrieval `Highly relevant`, answer `Partially correct / partially supported`. Note: Pipeline refused; manual review should decide whether available evidence should have supported an answer.
- `q042` (Finding first internship): retrieval `Highly relevant`, answer `Partially correct / partially supported`. Note: Pipeline refused; manual review should decide whether available evidence should have supported an answer.

## Evaluation Limitations

- Automated citation validation confirms citation format and label availability, not full factual entailment.
- Some advisory questions legitimately require cautious or insufficient-information responses.
- Local LLM outputs may vary between runs.
- The evaluation records passage previews and sources, but final grading should manually review representative answers before defense.

## Files

- Structured results: `C:/Users/HP/OneDrive/Documents/ChatGPT/ceng-ai-advisor/docs/rag-comprehensive-evaluation-results.json`
- Case set: `C:/Users/HP/OneDrive/Documents/ChatGPT/ceng-ai-advisor/tests/rag_comprehensive_evaluation_cases.json`
