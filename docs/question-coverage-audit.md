# Question Coverage Audit

## Scope

This audit reviews the 60 representative questions from `ceng-questions.pdf` against the 44 accepted sources currently recorded in `knowledge_base/sources.json`.

No new sources were collected. No URLs were added. No preprocessing, chunking, embeddings, ChromaDB, Ollama, RAG, chatbot, frontend, or backend work was performed.

## Coverage Scale

- **Strong:** One or more authoritative sources directly support the information needed.
- **Partial:** Useful related evidence exists, but an important part of the question is not directly supported.
- **Weak:** Only indirect or general evidence exists.
- **Missing:** No suitable evidence exists.

## Audit Table

| # | Short question/topic | Category/categories | Status | Supporting source IDs | Evidence explanation | Remaining evidence needed |
|---:|---|---|---|---|---|---|
| 1 | What is Computer Engineering? | Department Information, Common Misconceptions | Strong | src_001, src_009, src_042 | Official OSTIM and ACM sources define the discipline and computing subfields. | None critical. |
| 2 | What do students study? | Curriculum | Strong | src_003, src_004, src_009 | OSTIM curriculum and course-content pages directly show study areas. | None critical. |
| 3 | Is it the right major for me? | Department Information, Student Life, Specializations | Partial | src_001, src_005, src_043, src_044 | Sources explain the program and specialization options, but "right for me" requires personal advising logic. | More advising/self-assessment guidance for choosing engineering majors. |
| 4 | Computer Engineering vs Software Engineering | Department Information, Common Misconceptions | Strong | src_009, src_042 | ACM computing guidance distinguishes Computer Engineering from other computing disciplines. | A stronger Software Engineering-specific professional comparison could help. |
| 5 | Computer Engineering vs Computer Science | Department Information, Common Misconceptions | Strong | src_009, src_042 | ACM guidance directly differentiates computing subdisciplines. | None critical. |
| 6 | Hardware or software focus? | Department Information, Curriculum | Strong | src_001, src_003, src_004, src_042 | OSTIM and ACM sources show Computer Engineering combines hardware, software, and communications/systems. | None critical. |
| 7 | Student projects | Curriculum, Student Life, Skills | Strong | src_004, src_005, src_036, src_043 | Course contents, OSTIM difference page, and career resources support project and portfolio relevance. | More OSTIM-specific project examples would improve local detail. |
| 8 | Programming languages taught | Curriculum, Programming | Strong | src_003, src_004 | OSTIM curriculum/course pages are direct evidence. | None critical. |
| 9 | Prior programming experience | Programming, Common Misconceptions | Strong | src_004, src_039 | OSTIM course evidence and Brown CS beginner-pathway guidance support cautious beginner answers. | OSTIM-specific beginner support evidence would help. |
| 10 | Mathematics required | Mathematics, Curriculum | Strong | src_003, src_004 | OSTIM curriculum/course contents directly show mathematics courses. | More advising on how to improve math preparation. |
| 11 | Hardest engineering major? | Student Life, Mathematics | Weak | src_003, src_004, src_005 | Curriculum and workload can imply rigor, but no accepted source compares difficulty across engineering majors. | Reliable comparative workload/difficulty evidence. |
| 12 | No coding experience success | Programming, Student Life | Strong | src_039, src_034 | Brown CS guidance directly addresses no-prior-background pathways; NACE supports skill development. | OSTIM-specific support resources would help. |
| 13 | Weekly study hours | Student Life | Weak | src_003, src_004 | Curriculum shows course load, but no source provides typical weekly study-hour evidence. | University or student survey evidence about workload/study time. |
| 14 | Teamwork importance | Skills, Student Life | Strong | src_034, src_012, src_038 | NACE and professional skills sources support teamwork/collaboration as career-relevant. | None critical. |
| 15 | Skills to develop | Skills, Employment | Strong | src_014, src_015, src_016, src_031, src_034, src_038 | Multiple professional, industry, and employer sources identify technical and professional skills. | More Turkey employer evidence would help. |
| 16 | Find a job in Turkey | Employment, Career Opportunities | Partial | src_021, src_022, src_025, src_026, src_027 | Turkey ICT and graduate-employment sources support labor-market context, but not exact OSTIM/Computer Engineering placement rates. | Turkey Computer Engineering graduate outcomes and ICT occupation-level demand. |
| 17 | Good career in AI era | Career Opportunities, AI, Future Technologies | Strong | src_010, src_017, src_026, src_031, src_034 | Labor-market and future-jobs sources support continued demand for technology skills. | Turkey-specific AI-era employment evidence would help. |
| 18 | Will AI replace engineers? | AI, Future Technologies, Common Concerns | Partial | src_017, src_031, src_034 | Sources support changing skills and AI-driven labor transformation, but not a direct replacement/non-replacement conclusion. | Balanced AI impact studies specific to software/computing work. |
| 19 | Industries that hire graduates | Career Opportunities, Employment | Strong | src_010, src_011, src_012, src_025, src_026 | BLS and ICT sector sources identify employing sectors and technology areas. | Turkey employer/company examples could improve local grounding. |
| 20 | Work abroad | Remote Work, Employment | Strong | src_028, src_029, src_030 | Europass, EU Blue Card, and ENIC-NARIC support qualification and mobility considerations. | Country-specific rules for target countries, if later needed. |
| 21 | Work remotely | Remote Work, Work-Life Balance | Partial | src_019, src_032, src_026, src_037 | Remote/hybrid work evidence exists, but not specifically for Computer Engineers in Turkey. | Turkey/software-specific remote work evidence. |
| 22 | In-demand jobs today | Career Opportunities, Employment, Skills | Strong | src_010, src_011, src_012, src_014, src_016, src_017, src_026 | Labor, O*NET, industry, and future-jobs sources support in-demand computing roles. | Turkey occupation-level demand evidence would improve local answers. |
| 23 | Highest-demand specialization | Specializations, Employment | Partial | src_012, src_016, src_017, src_026, src_043 | Sources support growing areas, but do not rank all specializations consistently. | Comparative demand data by specialization, preferably Turkey-specific. |
| 24 | Start own software company | Entrepreneurship | Strong | src_020, src_025 | SBA gives business-start guidance; Turkey ICT sector evidence supports market context. | Turkey startup ecosystem guidance would improve local relevance. |
| 25 | Job market saturation | Employment, Future Technologies | Partial | src_010, src_017, src_021, src_026 | Outlook and labor-market sources support demand context, but none directly measure saturation. | Reliable saturation or graduate-supply-vs-demand analysis. |
| 26 | Opportunities in next 10 years | Future Technologies, Employment | Strong | src_010, src_011, src_012, src_013, src_017, src_026 | BLS outlooks, WEF, and ICT sources provide forward-looking evidence. | Turkey-specific long-term forecasts would help. |
| 27 | Future-proof career | Future Technologies, Career Opportunities | Partial | src_016, src_017, src_031, src_034 | Sources support adaptability and future skills but cannot guarantee "future-proof" status. | More balanced evidence on risks and reskilling. |
| 28 | No internship experience | Internships, Employment | Partial | src_018, src_037, src_036 | Sources show internships matter and alternatives can demonstrate skills, but no direct outcome evidence for no internship. | Evidence on outcomes for graduates without internships. |
| 29 | Low GPA | Employment | Partial | src_033, src_036, src_031 | NACE and Berkeley support nuanced GPA/skills framing, but not low-GPA outcome probabilities. | Employer or graduate-outcome evidence about low GPA. |
| 30 | GPA vs personal projects | Employment, Skills | Strong | src_033, src_035, src_036, src_031 | Sources support skills-based hiring, portfolio value, and careful GPA resume guidance. | Turkey-specific employer evidence would improve local answers. |
| 31 | Average starting salary | Salaries | Partial | src_010, src_011, src_012, src_013, src_021, src_023, src_024 | U.S. occupation pay and Turkey sector/field earnings exist, but not exact Turkey CENG starting salary. | Current Turkey Computer Engineering graduate salary data. |
| 32 | Highest-paying specialization in Turkey | Salaries, Specializations | Weak | src_023, src_024, src_012, src_013 | Salary sources are sector/occupation-level or international, not Turkey specialization-level. | Transparent Turkey salary evidence by specialization. |
| 33 | Time to senior software engineer | Career Opportunities, Skills | Partial | src_038, src_031 | SFIA describes responsibility growth but not universal years. | Credible career-ladder data if a source-specific range is needed. |
| 34 | Become AI engineer | AI, Graduate Studies, Career Opportunities | Strong | src_013, src_017, src_016, src_031, src_008 | Research, future-jobs, and skills sources support AI pathway evidence. | Practical AI role requirements from more technical sources could help. |
| 35 | Become cybersecurity specialist | Cybersecurity, Specializations | Strong | src_012, src_016, src_008, src_043 | BLS, Linux Foundation, OSTIM research, and specialization sources support cybersecurity pathways. | More certification/skills roadmap evidence could help later. |
| 36 | First programming language | Programming | Partial | src_003, src_004, src_039 | Curriculum and beginner-course sources identify languages/pathways but do not recommend a universal first language. | Educational guidance on language choice for beginners. |
| 37 | Technologies before graduation | Skills, Employment | Strong | src_014, src_015, src_016, src_031, src_034, src_038 | Professional, technical, and employer sources support key technology and career-readiness skills. | Turkey employer tech-stack evidence would help. |
| 38 | Web, mobile, AI, or cybersecurity | Specializations, Skills | Partial | src_012, src_016, src_017, src_026, src_043 | Sources identify growing domains, but personal fit and ranking are not directly answered. | Student advising framework and comparative specialization evidence. |
| 39 | Linux importance | Skills | Strong | src_014, src_016 | O*NET and Linux Foundation support Linux/open-source relevance to technical careers. | None critical. |
| 40 | Git and GitHub importance | Skills, Programming | Strong | src_015, src_014, src_036 | GitHub Docs and career resources support version control, collaboration, and portfolio use. | None critical. |
| 41 | Internship importance | Internships | Strong | src_007, src_018, src_037, src_034 | OSTIM workplace documents and NACE internship/employer evidence directly support importance. | Turkey-specific employer evidence would help. |
| 42 | Find first internship | Internships, Employment | Partial | src_037, src_036, src_034 | Sources support internship sourcing and resume preparation but not a complete first-internship strategy. | Local university/career-center guidance for first internships. |
| 43 | CV content | Employment, Skills | Strong | src_036, src_035, src_034 | Berkeley, MIT, and NACE support resume sections, projects, examples, and skill articulation. | Turkey CV norms could help. |
| 44 | Build portfolio | Employment, Skills | Strong | src_035, src_036, src_015 | MIT portfolio guidance, Berkeley resume guidance, and GitHub Docs support portfolio building. | More Computer Engineering portfolio examples could help. |
| 45 | Hackathons/coding competitions | Student Life, Skills | Partial | src_034, src_036, src_005 | NACE mentions hackathons as skill-building, but no dedicated evidence on competitions. | Reliable hackathon/competition learning or employer-value source. |
| 46 | Master's degree necessary | Graduate Studies, Career Opportunities | Strong | src_013, src_044, src_031 | BLS and MIT distinguish research/advanced roles from broader career paths. | Field-specific graduate-degree evidence for AI/cybersecurity could help. |
| 47 | AI without master's | AI, Graduate Studies | Partial | src_013, src_017, src_031, src_044 | Sources support graduate-school value and AI skill demand, but not a direct "AI without master's" answer. | AI job-requirement evidence distinguishing applied vs research roles. |
| 48 | Graduate school or work | Graduate Studies, Employment | Strong | src_044, src_021, src_031 | MIT guidance and employment indicators support decision framing. | Turkey-specific graduate outcomes would help. |
| 49 | Right field of CENG | Specializations | Partial | src_043, src_044, src_031 | Specialization map and self-assessment guidance support exploration, but not individualized selection. | Stronger advising framework for matching interests to specializations. |
| 50 | Don't enjoy coding | Common Misconceptions, Specializations | Partial | src_042, src_043, src_011, src_014 | Sources show CENG includes hardware, systems, networks, and security, but coding remains important. | Evidence on non-coding-heavy CENG roles and required coding levels. |
| 51 | Discover specialization interest | Specializations, Student Life | Partial | src_043, src_044, src_035, src_036 | Sources support exploring subfields, projects, portfolios, and self-assessment. | More explicit specialization exploration guidance. |
| 52 | Fastest-growing specialization | Future Technologies, Specializations | Partial | src_012, src_017, src_026, src_016 | Sources identify growth areas but not a definitive CENG specialization ranking. | Comparative growth data across specializations. |
| 53 | Work-life balance | Work-Life Balance | Partial | src_019, src_032 | ILO and Eurofound support general work-life and remote-work evidence. | Software/Computer Engineering-specific work-life evidence. |
| 54 | Stressful profession | Work-Life Balance, Student Life | Weak | src_019, src_032 | General working-time evidence exists, but no computing-specific stress source is accepted. | Reliable computing/software stress and wellbeing evidence. |
| 55 | Digital nomads | Remote Work | Partial | src_028, src_029, src_032 | International work and remote-work sources support considerations, but not digital nomad legality/tax detail. | Official digital-nomad/remote-work rules for target countries. |
| 56 | All day coding? | Common Misconceptions | Strong | src_042, src_043, src_014, src_038 | ACM, UIUC, O*NET, and SFIA show a range of tasks beyond just coding. | None critical. |
| 57 | Only for people good at math? | Mathematics, Common Misconceptions | Partial | src_003, src_004, src_039, src_041 | Math requirements and beginner pathways exist, but no direct source addresses the math stereotype. | Educational guidance on math preparation and growth. |
| 58 | Women successful in CENG | Common Misconceptions, Employment | Strong | src_040, src_041 | NCWIT provides participation data and misconception guidance. | Turkey-specific women-in-computing evidence would help. |
| 59 | Too late to start programming at university? | Programming, Common Misconceptions | Strong | src_039, src_041 | Brown CS directly supports beginner entry pathways; NCWIT supports misconception framing. | OSTIM-specific beginner support evidence would help. |
| 60 | Why choose CENG over another engineering discipline? | Department Information, Career Opportunities | Partial | src_001, src_009, src_017, src_026, src_042 | Sources support what CENG offers and career relevance, but not a direct comparative engineering-major decision framework. | Comparative engineering-major guidance and student fit criteria. |

## Summary Counts

- **Strong:** 32
- **Partial:** 24
- **Weak:** 4
- **Missing:** 0

## Main Audit Conclusion

The knowledge base can already support many factual and advisory questions, but several answers must remain cautious. The weakest areas are exact Turkey-specific salaries, specialization rankings, workload/study-hour expectations, stress, low GPA outcomes, no-internship outcomes, and Turkey-specific employer evaluation practices.
