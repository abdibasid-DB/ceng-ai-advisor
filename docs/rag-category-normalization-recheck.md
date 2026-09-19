# WEX428 Retrieval Category Normalization Recheck

Generated at: `2026-09-18T19:21:07+00:00`

This report reclassifies retrieval-quality labels from the saved comprehensive evaluation retrieval evidence only. It does not rerun retrieval, regenerate LLM answers, change answer-quality labels, or modify production RAG behavior.

## Category Compatibility Map

- `AI -> artificial_intelligence`: The evaluation shorthand `AI` refers to the indexed `artificial_intelligence` category.
- `cybersecurity -> specializations`: Cybersecurity appears as a computing specialization/subdiscipline in advising evidence.
- `employment -> career_opportunities`: `career_opportunities` is an employment-focused indexed category for job/role evidence.
- `local_job_market -> employment`: Local job-market evidence is stored under the broader indexed `employment` category.
- `mathematics -> curriculum`: Math requirements are represented in curriculum/course evidence rather than a separate indexed math category.
- `programming -> skills_and_technologies`: Programming-language/tool evidence is a technical-skills subset in the indexed corpus.
- `remote_work -> work_life_balance`: Remote/hybrid work evidence overlaps with work-life balance sources when evaluating work-style questions.
- `skills -> skills_and_technologies`: The evaluation label `skills` maps to the indexed technical/professional skills category.

## Old Retrieval Totals

| Label | Count |
|---|---:|
| Highly relevant | 9 |
| Irrelevant | 41 |
| Partially relevant | 1 |
| Relevant | 29 |

## Corrected Retrieval Totals

| Label | Count |
|---|---:|
| Highly relevant | 21 |
| Irrelevant | 18 |
| Partially relevant | 2 |
| Relevant | 39 |

## Changed Cases

- `q009`: `Relevant` -> `Highly relevant`; matched categories: programming, skills_and_technologies
- `q011`: `Irrelevant` -> `Relevant`; matched categories: curriculum, skills_and_technologies
- `q013`: `Irrelevant` -> `Relevant`; matched categories: skills_and_technologies
- `q017`: `Relevant` -> `Highly relevant`; matched categories: future_technologies, artificial_intelligence
- `q018`: `Irrelevant` -> `Highly relevant`; matched categories: artificial_intelligence, artificial_intelligence
- `q024`: `Irrelevant` -> `Relevant`; matched categories: skills_and_technologies, skills_and_technologies
- `q030`: `Irrelevant` -> `Relevant`; matched categories: skills_and_technologies, skills_and_technologies, skills_and_technologies
- `q033`: `Irrelevant` -> `Highly relevant`; matched categories: skills_and_technologies, skills_and_technologies
- `q034`: `Irrelevant` -> `Highly relevant`; matched categories: artificial_intelligence, skills_and_technologies
- `q035`: `Irrelevant` -> `Relevant`; matched categories: skills_and_technologies, skills_and_technologies
- `q037`: `Irrelevant` -> `Relevant`; matched categories: skills_and_technologies, skills_and_technologies, skills_and_technologies
- `q038`: `Irrelevant` -> `Highly relevant`; matched categories: skills_and_technologies, skills_and_technologies
- `q040`: `Relevant` -> `Highly relevant`; matched categories: skills_and_technologies, programming
- `q043`: `Relevant` -> `Highly relevant`; matched categories: employment, skills_and_technologies
- `q045`: `Irrelevant` -> `Partially relevant`; matched categories: skills_and_technologies, skills_and_technologies, skills_and_technologies, skills_and_technologies
- `q049`: `Irrelevant` -> `Highly relevant`; matched categories: skills_and_technologies, skills_and_technologies
- `q051`: `Irrelevant` -> `Relevant`; matched categories: skills_and_technologies, skills_and_technologies
- `q053`: `Irrelevant` -> `Relevant`; matched categories: work_life_balance
- `q057`: `Irrelevant` -> `Relevant`; matched categories: curriculum, curriculum, skills_and_technologies
- `p006`: `Irrelevant` -> `Relevant`; matched categories: skills_and_technologies, skills_and_technologies
- `p007`: `Irrelevant` -> `Highly relevant`; matched categories: artificial_intelligence, artificial_intelligence
- `p008`: `Irrelevant` -> `Highly relevant`; matched categories: skills_and_technologies, skills_and_technologies
- `p011`: `Irrelevant` -> `Relevant`; matched categories: skills_and_technologies, skills_and_technologies, skills_and_technologies
- `p015`: `Irrelevant` -> `Relevant`; matched categories: skills_and_technologies, skills_and_technologies, skills_and_technologies
- `p016`: `Irrelevant` -> `Relevant`; matched categories: skills_and_technologies, skills_and_technologies
- `p017`: `Irrelevant` -> `Highly relevant`; matched categories: skills_and_technologies, skills_and_technologies, skills_and_technologies, skills_and_technologies
- `p018`: `Irrelevant` -> `Relevant`; matched categories: curriculum, skills_and_technologies, curriculum

## Remaining Irrelevant Retrieval Cases

- `q003` (Choosing Computer Engineering): expected ['department_information', 'common_misconceptions', 'employment']; retrieved ['programming', 'skills_and_technologies', 'skills_and_technologies']
- `q006` (Hardware and software balance): expected ['department_information', 'curriculum']; retrieved ['skills_and_technologies', 'skills_and_technologies', 'skills_and_technologies', 'skills_and_technologies']
- `q014` (Teamwork skills): expected ['skills', 'projects', 'employment']; retrieved ['artificial_intelligence', 'artificial_intelligence', 'future_technologies']
- `q015` (Student skills development): expected ['skills', 'programming', 'employment']; retrieved ['department_information', 'department_information', 'curriculum']
- `q019` (Hiring industries): expected ['employment', 'department_information']; retrieved ['future_technologies', 'skills_and_technologies', 'skills_and_technologies']
- `q020` (Working abroad): expected ['employment', 'graduate_studies', 'remote_work']; retrieved ['skills_and_technologies', 'skills_and_technologies', 'future_technologies']
- `q031` (Starting salary): expected ['salary', 'employment', 'local_job_market']; retrieved ['remote_work', 'future_technologies', 'skills_and_technologies']
- `q047` (AI work without master's): expected ['AI', 'graduate_studies', 'employment']; retrieved ['future_technologies', 'skills_and_technologies', 'skills_and_technologies']
- `q054` (Professional stress): expected ['employment', 'common_misconceptions']; retrieved ['work_life_balance', 'skills_and_technologies', 'future_technologies']
- `q055` (Digital nomad career): expected ['remote_work', 'employment']; retrieved ['skills_and_technologies', 'future_technologies', 'future_technologies']
- `q056` (Coding-only misconception): expected ['common_misconceptions', 'department_information', 'employment']; retrieved ['work_life_balance', 'skills_and_technologies', 'skills_and_technologies', 'skills_and_technologies']
- `q058` (Women in Computer Engineering): expected ['common_misconceptions', 'employment']; retrieved ['skills_and_technologies', 'skills_and_technologies', 'future_technologies']
- `p001` (Computer Engineering definition paraphrase): expected ['department_information', 'curriculum']; retrieved ['student_life', 'skills_and_technologies', 'programming']
- `p003` (No coding background paraphrase): expected ['programming', 'common_misconceptions', 'skills']; retrieved ['curriculum', 'curriculum', 'curriculum', 'department_information', 'department_information']
- `p004` (Hardware and software balance paraphrase): expected ['department_information', 'curriculum']; retrieved ['skills_and_technologies', 'skills_and_technologies', 'future_technologies']
- `p012` (International work paraphrase): expected ['employment', 'graduate_studies', 'remote_work']; retrieved ['department_information', 'curriculum', 'student_life']
- `p013` (Future technologies paraphrase): expected ['future_technologies', 'AI', 'cybersecurity', 'employment']; retrieved ['skills_and_technologies', 'skills_and_technologies', 'skills_and_technologies']
- `p019` (Women in computing paraphrase): expected ['common_misconceptions', 'employment']; retrieved ['skills_and_technologies', 'skills_and_technologies', 'future_technologies']
