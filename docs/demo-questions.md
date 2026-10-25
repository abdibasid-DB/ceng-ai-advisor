# Demo questions

Ten questions to demonstrate the advisor live. Each produced a good answer in the final evaluation ([docs/final-evaluation-20261025](final-evaluation-20261025/report.md)) and gave the identical answer and sources when it was run again ([demo-check-results.json](final-evaluation-20261025/demo-check-results.json)). The answers and sources below are copied from those result files. The system uses temperature 0 and seed 42, so with Ollama started with `LLAMA_ARG_CACHE_RAM=0` the live app should give the same text (see README, Backend configuration).

Selection rules:

- labelled `correct_evidence_supported` (or a correct refusal) in the final run and in the 2026-10-23 run; the exception is S127, whose source was only added on 2026-10-25;
- NLI entailment ≥ 0.5 for every cited sentence where it was scored;
- read against the cited passages by hand.

**The four specification questions are not included.** In the final run, SPEC1 was refused. SPEC2 and SPEC3 contain a claim their cited passage does not make. SPEC4 is mostly supported but hardly addresses mathematics. See [the evaluation report](final-evaluation-20261025/report.md#specification-questions).

| # | Case | Question | Kind | Time in final run |
|---:|---|---|---|---:|
| 1 | F001 | What is Computer Engineering? | Definition of the field | 34 s |
| 2 | F007 | Do computer engineers build physical devices or just apps? | Hardware and software | 41 s |
| 3 | C026 | Are senior design projects part of CE education? | Curriculum structure | 34 s |
| 4 | A082 | What parts of engineering work are changed by generative AI? | Generative AI and engineering work | 39 s |
| 5 | A073 | What AI skills are useful besides prompt engineering? | AI skills | 34 s |
| 6 | Y086 | Is cybersecurity more software or hardware? | Cybersecurity | 32 s |
| 7 | R102 | What if I graduate without internship experience? | Career: no internship | 39 s |
| 8 | S127 | OSTIMTECH social clubs/student communities? | OSTİM: student communities | 37 s |
| 9 | T186 | Tell me about the curriculum. → Does it include Linux? | Follow-up pair | 68 s |
| 10 | O166 | How do I bake sourdough bread? | Out of scope | 0 s |

## 1. Definition of the field (F001)

**Question:** What is Computer Engineering?

**Answer:**

> Computer Engineering is a four-year curriculum that focuses on the synthesis of electrical engineering and computer science, aimed at designing and constructing processor-based systems that include hardware, software, and communications components [S1]. Graduates of this program are expected to design and implement systems that integrate software and hardware devices, such as those found in cellular communications, consumer electronics, medical imaging and devices, alarm systems, and military technologies [S1].

**Sources shown:**

- [S1] Curricular Guidance — ACM Committee for Computing Education in Community Colleges (src_042) <https://ccecc.acm.org/guidance>

Final run: `answered`, `correct_evidence_supported`; NLI: 2 of 2 cited sentences entailed; second run identical.

## 2. Hardware and software (F007)

**Question:** Do computer engineers build physical devices or just apps?

**Answer:**

> Computer engineers build both physical devices and apps [S1]. The context indicates that computer engineers design and construct processor-based systems that include hardware, software, and communications components [S2]. This encompasses a wide range of physical devices such as cellular communications, consumer electronics, medical imaging devices, and military technologies [S2] [S3]. Additionally, they work on distributed computing environments and embedded computer systems, such as those found in aircraft, spacecraft, and automobile control systems [S1].

**Sources shown:**

- [S1] Computer Engineering Curricula 2016 — Association for Computing Machinery and IEEE Computer Society (src_067) <https://www.acm.org/binaries/content/assets/education/ce2016-final-report.pdf>
- [S2] Curricular Guidance — ACM Committee for Computing Education in Community Colleges (src_042) <https://ccecc.acm.org/guidance>
- [S3] Curricular Guidance: the sub-disciplines of computing (computer engineering, computer science, software engineering, information technology) — ACM Committee for Computing Education in Community Colleges (src_128) <https://ccecc.acm.org/guidance>

Final run: `answered`, `correct_evidence_supported`; NLI: 4 of 4 cited sentences entailed; second run identical.

## 3. Curriculum structure (C026)

**Question:** Are senior design projects part of CE education?

**Answer:**

> The curriculum includes a two-course sequence in the senior year, known as CE Design I and CE Design II, which is a culminating design experience [S1]. This is detailed in [S1], which states that the culminating design experience is a two-course sequence in the senior year of the curriculum.

**Sources shown:**

- [S1] Computer Engineering Curricula 2016 — Association for Computing Machinery and IEEE Computer Society (src_067) <https://www.acm.org/binaries/content/assets/education/ce2016-final-report.pdf>

Final run: `answered`, `correct_evidence_supported`; NLI: 2 of 2 cited sentences entailed; second run identical.

## 4. Generative AI and engineering work (A082)

**Question:** What parts of engineering work are changed by generative AI?

**Answer:**

> Generative AI has the potential to change various aspects of engineering work, particularly in software development [S2]. In the context of the [S2] report, it is mentioned that professional developers are assessing the value of their work differently when using generative artificial intelligence (AI). The [S3] report indicates that organizations are planning to use AI for tasks such as data analysis and reporting, IT infrastructure monitoring, and software development.

**Sources shown:**

- [S2] How Gen AI Affects the Value of Development Work — DORA, Google (src_053) <https://research.google/pubs/how-gen-ai-affects-the-value-of-development-work/>
- [S3] 2024 State of Tech Talent Report — The Linux Foundation (src_016) <https://www.linuxfoundation.org/research/open-source-jobs-report-2024>

Final run: `answered`, `correct_evidence_supported`; NLI: 3 of 3 cited sentences entailed; second run identical.

## 5. AI skills (A073)

**Question:** What AI skills are useful besides prompt engineering?

**Answer:**

> AI skills besides prompt engineering include understanding code, debugging, security, data, systems, architecture, and collaboration [S4]. In the source [S4], it is mentioned that AI is changing workflows and creating new kinds of projects, but it also increases the value of fundamentals such as understanding code, debugging, security, data, systems, architecture, and collaboration.

**Sources shown:**

- [S4] Curated note: Octoverse 2024: AI leads Python to top language as the number of global developers surges — CENG AI Advisor summary based on GitHub (src_087) <https://github.blog/news-insights/octoverse/octoverse-2024/>

Final run: `answered`, `correct_evidence_supported`; NLI: 2 of 2 cited sentences entailed; second run identical.

## 6. Cybersecurity (Y086)

**Question:** Is cybersecurity more software or hardware?

**Answer:**

> Cybersecurity is not exclusively software or hardware; it involves both [S1] [S2] [S3]. In Computer Engineering, cybersecurity is a computing-based discipline that encompasses technology, people, information, and processes to enable assured operations in the context of adversaries [S3].

**Sources shown:**

- [S1] Curated note: Cybersecurity Curricular Guidelines CSEC 2017 — CENG AI Advisor summary based on ACM, IEEE Computer Society, AIS SIGSEC, and IFIP WG 11.8 (src_085) <https://cybered.acm.org/>
- [S2] Curated note: Cyber Career Pathways Tool — CENG AI Advisor summary based on Cybersecurity and Infrastructure Security Agency / NICCS (src_094) <https://niccs.cisa.gov/workforce-development/cyber-career-pathways-tool>
- [S3] Curricular Guidance: the sub-disciplines of computing (computer engineering, computer science, software engineering, information technology) — ACM Committee for Computing Education in Community Colleges (src_128) <https://ccecc.acm.org/guidance>

Final run: `answered`, `correct_evidence_supported`; NLI: 2 of 2 cited sentences entailed; second run identical.

## 7. Career: no internship (R102)

**Question:** What if I graduate without internship experience?

**Answer:**

> If a student graduates without internship experience, they may face challenges in certain industry environments where prior industry experience is valued [S1]. Engaging with professionals in the field can provide valuable insights into the most important skills and opportunities available in the industry [S2].

**Sources shown:**

- [S1] Computer Engineering Curricula 2016 — Association for Computing Machinery and IEEE Computer Society (src_067) <https://www.acm.org/binaries/content/assets/education/ce2016-final-report.pdf>
- [S2] Write a Resume/CV — University of Pennsylvania Career Services (src_074) <https://careerservices.upenn.edu/channels/resume/>

Final run: `answered`, `correct_evidence_supported`; NLI: 2 of 2 cited sentences entailed; second run identical.

## 8. OSTİM: student communities (S127)

**Question:** OSTIMTECH social clubs/student communities?

**Answer:**

> OSTİM Technical University has several student communities, including those in the Software, AI & Tech category [S1]. Specifically, there are student clubs such as Yapay Zeka, Pandora AI, Siber Güvenlik, Software Club, Google Developer Student Clubs, Huawei Student Developers, IEEE, Yönetim Bilişim Sistemleri, and Sosyal Teknoloji [S1].

**Sources shown:**

- [S1] Öğrenci Topluluklarımız — OSTİM Teknik Üniversitesi Sağlık, Kültür ve Spor Daire Başkanlığı (src_122) <https://sks.ostimteknik.edu.tr/ogrenci-topluluklarimiz>

Final run: `answered`, `correct_evidence_supported`; NLI: 2 of 2 cited sentences entailed; second run identical.

Note: Answered from src_122, the club list added on 2026-10-25. The 2026-10-23 run refused this question.

## 9. Follow-up pair (T186)

**First question:** Tell me about the curriculum.

**Answer:**

> The curriculum is outlined in detail in the report, which is available on the Association for Computing Machinery and IEEE Computer Society's website [S1] [S2] [S3].

**Follow-up:** Does it include Linux?

Rewritten for retrieval: *What specific topics related to Linux are covered in the curriculum?*

**Answer:**

> The curriculum for CENG 303 Operating Systems Design & Construction at OSTIM Technical University covers specific topics related to Linux, including process management, thread scheduling, synchronization, deadlocks, memory management, file systems, input/output systems, and security [S1]. These topics are essential for understanding how to design and construct operating systems, and given the context that most clusters are Linux-based, students will need to gain proficiency in using the Linux command line to navigate and run code [S2].

**Sources shown:**

- [S1] Course Contents: CENG 303 Operating Systems Design & Construction (Linux or Windows) — OSTIM Technical University - Department of Computer Engineering (English) (src_130) <https://mfcs.ostimteknik.edu.tr/course-contents>
- [S2] Computing Competencies for Undergraduate Data Science Curricula — Association for Computing Machinery Data Science Task Force (src_069) <https://www.acm.org/binaries/content/assets/education/curricula-recommendations/dstf_ccdsc2021.pdf>

Final run: `answered`, `correct_evidence_supported`; NLI: 2 of 2 cited sentences entailed; second run identical.

Note: Shows the follow-up rewrite: "it" becomes the curriculum, and the answer comes from the OSTİM CENG 303 course page. The first-turn answer is thin: it only points to the ACM/IEEE report. Also, src_130 lists CENG 303 as "(Linux or Windows)", and the topics it names are general operating-system topics, so "topics related to Linux" stretches the source a little.

## 10. Out of scope (O166)

**Question:** How do I bake sourdough bread?

**Answer:**

> I am a Computer Engineering student advisor. I can help with Computer Engineering education, curriculum, courses, skills, careers, internships, AI, cybersecurity, programming, and related study paths.

**Sources shown:**

- none (no retrieval)

Final run: `out_of_scope`, `correct_insufficient_information`; NLI: –; second run identical.

Note: Fixed scope reply; no retrieval and no LLM call.
