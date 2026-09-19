# WEX428 Comprehensive RAG Evaluation Report

Generated at: `2026-09-18T18:21:18+00:00`

## Scope

This evaluation runs the existing local RAG pipeline against all 60 representative questions from `ceng-questions.pdf` plus paraphrased/unseen questions across major categories. It does not modify production retrieval, embeddings, the vector database, the LLM, or prompts.

Answer-quality labels are an automated preliminary rubric based on retrieval relevance, answer status, and citation validation. They are useful for project evaluation, but they do not replace manual claim-level factual review.

## Summary

- Total cases: 80
- Original questions tested: 60
- Paraphrased/unseen questions tested: 20
- Answered cases with valid citations: 57/57
- Appropriate refusals: 6

## Retrieval Quality Results

| Label | Count |
|---|---:|
| Highly relevant | 9 |
| Irrelevant | 41 |
| Partially relevant | 1 |
| Relevant | 29 |

## Answer Status Results

| Label | Count |
|---|---:|
| answered | 57 |
| error | 8 |
| insufficient_information | 12 |
| out_of_scope | 3 |

## Answer-Quality Results

| Label | Count |
|---|---:|
| Appropriate refusal / insufficient information | 6 |
| Correct / well-supported | 32 |
| Partially correct / partially supported | 9 |
| Unsupported or incorrect | 33 |

## Weak Categories / Topics

- AI engineer pathway: 1 case(s) - q034
- AI replacement concern: 1 case(s) - q018
- AI work without master's: 1 case(s) - q047
- AI-era career comparison paraphrase: 1 case(s) - p007
- Academic difficulty: 1 case(s) - q011
- Choosing Computer Engineering: 1 case(s) - q003
- Choosing field: 1 case(s) - q049
- Choosing specialization focus: 1 case(s) - q038
- Coding-only misconception: 1 case(s) - q056
- Computer Engineering curriculum scope: 1 case(s) - q002
- Computer Engineering definition paraphrase: 1 case(s) - p001
- Computer Engineering versus Computer Science: 1 case(s) - q005
- Cybersecurity career paraphrase: 1 case(s) - p008
- Cybersecurity specialist pathway: 1 case(s) - q035
- Digital nomad career: 1 case(s) - q055
- Discovering specialization interests: 1 case(s) - q051
- Entrepreneurship: 1 case(s) - q024
- Entrepreneurship paraphrase: 1 case(s) - p016
- Future technologies paraphrase: 1 case(s) - p013
- Future-proof career concern: 1 case(s) - q027
- GPA versus projects: 1 case(s) - q030
- Git and GitHub importance: 1 case(s) - q040
- Hackathons and competitions: 1 case(s) - q045
- Hardware and software balance: 1 case(s) - q006
- Hardware and software balance paraphrase: 1 case(s) - p004
- Hardware-oriented specialization paraphrase: 1 case(s) - p015
- Hiring industries: 1 case(s) - q019
- International work paraphrase: 1 case(s) - p012
- Math anxiety paraphrase: 1 case(s) - p018
- Math-only misconception: 1 case(s) - q057
- No coding background paraphrase: 1 case(s) - p003
- OSTIM Computer Engineering curriculum paraphrase: 1 case(s) - p002
- Portfolio projects paraphrase: 1 case(s) - p006
- Professional stress: 1 case(s) - q054
- Projects versus GPA paraphrase: 1 case(s) - p011
- Senior engineer timeline: 1 case(s) - q033
- Specialization choice paraphrase: 1 case(s) - p017
- Starting salary: 1 case(s) - q031
- Student CV: 1 case(s) - q043
- Student skills development: 1 case(s) - q015
- Student workload: 1 case(s) - q013
- Teamwork skills: 1 case(s) - q014
- Technologies before graduation: 1 case(s) - q037
- Women in Computer Engineering: 1 case(s) - q058
- Women in computing paraphrase: 1 case(s) - p019
- Work-life balance: 1 case(s) - q053
- Working abroad: 1 case(s) - q020

## Representative Successful Examples

- `q001` (Computer Engineering definition): retrieval `Relevant`, answer `Correct / well-supported`.
- `q004` (Computer Engineering versus Software Engineering): retrieval `Relevant`, answer `Correct / well-supported`.
- `q007` (Student projects): retrieval `Relevant`, answer `Correct / well-supported`.
- `q008` (Programming languages in curriculum): retrieval `Highly relevant`, answer `Correct / well-supported`.
- `q009` (Prior programming experience): retrieval `Relevant`, answer `Correct / well-supported`.

## Representative Failure / Caution Examples

- `q002` (Computer Engineering curriculum scope): retrieval `Highly relevant`, answer `Unsupported or incorrect`. Note: missing inline [S#] citation
- `q003` (Choosing Computer Engineering): retrieval `Irrelevant`, answer `Unsupported or incorrect`. Note: Answered with valid citation format, but retrieved categories did not match expectations.
- `q005` (Computer Engineering versus Computer Science): retrieval `Relevant`, answer `Unsupported or incorrect`. Note: answer appears incomplete or truncated
- `q006` (Hardware and software balance): retrieval `Irrelevant`, answer `Unsupported or incorrect`. Note: Answered with valid citation format, but retrieved categories did not match expectations.
- `q011` (Academic difficulty): retrieval `Irrelevant`, answer `Appropriate refusal / insufficient information`. Note: Pipeline refused because retrieved evidence was insufficient.
- `q013` (Student workload): retrieval `Irrelevant`, answer `Unsupported or incorrect`. Note: Answered with valid citation format, but retrieved categories did not match expectations.
- `q014` (Teamwork skills): retrieval `Irrelevant`, answer `Unsupported or incorrect`. Note: Answered with valid citation format, but retrieved categories did not match expectations.
- `q015` (Student skills development): retrieval `Irrelevant`, answer `Unsupported or incorrect`. Note: missing inline [S#] citation

## Evaluation Limitations

- Automated citation validation confirms citation format and label availability, not full factual entailment.
- Some advisory questions legitimately require cautious or insufficient-information responses.
- Local LLM outputs may vary between runs.
- The evaluation records passage previews and sources, but final grading should manually review representative answers before defense.

## Files

- Structured results: `docs/rag-comprehensive-evaluation-results.json`
- Case set: `tests/rag_comprehensive_evaluation_cases.json`
