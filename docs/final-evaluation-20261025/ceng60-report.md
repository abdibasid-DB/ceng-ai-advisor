# WEX428 Comprehensive RAG Evaluation Report

Generated at: `2026-10-25T16:59:34+00:00`

## Scope

This evaluation runs the existing local RAG pipeline against all 60 representative questions from `ceng-questions.pdf` plus paraphrased/unseen questions across major categories. It does not modify production retrieval, embeddings, the vector database, the LLM, or prompts.

Answer-quality labels are an automated preliminary rubric based on retrieval relevance, answer status, and citation validation. They are useful for project evaluation, but they do not replace manual claim-level factual review.

## Summary

- Total cases: 60
- Original questions tested: 60
- Paraphrased/unseen questions tested: 0
- Answered cases with valid citations: 37/37
- Appropriate refusals: 12

## Retrieval Quality Results

| Label | Count |
|---|---:|
| Highly relevant | 47 |
| Irrelevant | 5 |
| Relevant | 8 |

## Answer Status Results

| Label | Count |
|---|---:|
| answered | 37 |
| insufficient_information | 23 |

## Answer-Quality Results

| Label | Count |
|---|---:|
| Appropriate refusal / insufficient information | 12 |
| Correct / well-supported | 34 |
| Partially correct / partially supported | 11 |
| Unsupported or incorrect | 3 |

## Weak Categories / Topics

- AI work without master's: 1 case(s) - q047
- Choosing Computer Engineering: 1 case(s) - q003
- Choosing Computer Engineering over other engineering: 1 case(s) - q060
- Choosing specialization focus: 1 case(s) - q038
- Computer Engineering definition: 1 case(s) - q001
- Cybersecurity specialist pathway: 1 case(s) - q035
- Entrepreneurship: 1 case(s) - q024
- Finding first internship: 1 case(s) - q042
- Hackathons and competitions: 1 case(s) - q045
- Linux importance: 1 case(s) - q039
- Master's degree necessity: 1 case(s) - q046
- Math-only misconception: 1 case(s) - q057
- Student CV: 1 case(s) - q043
- Student workload: 1 case(s) - q013
- Succeeding without enjoying coding: 1 case(s) - q050
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
- `q013` (Student workload): retrieval `Irrelevant`, answer `Appropriate refusal / insufficient information`. Note: Pipeline refused because retrieved evidence was insufficient.
- `q024` (Entrepreneurship): retrieval `Relevant`, answer `Partially correct / partially supported`. Note: Pipeline refused; manual review should decide whether available evidence should have supported an answer.
- `q035` (Cybersecurity specialist pathway): retrieval `Highly relevant`, answer `Partially correct / partially supported`. Note: Pipeline refused; manual review should decide whether available evidence should have supported an answer.
- `q037` (Technologies before graduation): retrieval `Highly relevant`, answer `Partially correct / partially supported`. Note: Pipeline refused; manual review should decide whether available evidence should have supported an answer.
- `q038` (Choosing specialization focus): retrieval `Highly relevant`, answer `Partially correct / partially supported`. Note: Pipeline refused; manual review should decide whether available evidence should have supported an answer.
- `q039` (Linux importance): retrieval `Relevant`, answer `Partially correct / partially supported`. Note: Pipeline refused; manual review should decide whether available evidence should have supported an answer.

## Evaluation Limitations

- Automated citation validation confirms citation format and label availability, not full factual entailment.
- Some advisory questions legitimately require cautious or insufficient-information responses.
- Local LLM outputs may vary between runs.
- The evaluation records passage previews and sources, but final grading should manually review representative answers before defense.

## Files

- Structured results: `C:/Users/HP/OneDrive/Documents/ChatGPT/ceng-ai-advisor/docs/rag-comprehensive-evaluation-results.json`
- Case set: `C:/Users/HP/OneDrive/Documents/ChatGPT/ceng-ai-advisor/tests/rag_comprehensive_evaluation_cases.json`
