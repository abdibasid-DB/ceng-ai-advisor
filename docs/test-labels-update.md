# Source-label review, 2026-10-20

Base: `ce9eac1` on main. Read and reviewed all 360 questions (240 paraphrase variants of 60 originals, plus 120 unseen questions) against the requested processed texts. Existing source IDs, questions, IDs, variants and expected behaviors are preserved. Additions and note corrections only.

Scope: updated `src_058`; `src_095` through `src_125`, excluding `src_122` and `src_124`. `src_121.txt` is absent, leaving 29 available documents. No raw pages, external searches, model generation or reindexing were used as label evidence.

An expected source can support a qualified answer or correct a false premise; it does not license a broader claim than its text supports. Notes retain geography, dates, population, program distinctions and incomplete numeric thresholds. Topic-only matches were rejected. In particular, 2026-2027 tuition is not a verified 2027-2028 fee, a staff-pay policy is not a published student assistantship, and general doctoral rules do not establish an active CENG PhD.

| File | Reviewed | Rows with added sources | Source-ID additions | No source before | No source after | Newly sourced |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| retrieval_paraphrase_cases.json | 240 | 64 | 100 | 44 | 20 | 24 |
| unseen_coverage_cases.json | 120 | 17 | 19 | 37 | 27 | 10 |

## Previously unsourced questions that now have evidence, by topic

Paraphrase counts include all four variants; distinct original-question counts are also shown. Unseen topics use the existing `topic_area`; paraphrase topics below are descriptive review groupings because that file has no topic field. All other topics gained zero previously unsourced questions.

| Topic | Paraphrase rows | Distinct paraphrase originals | Unseen rows |
| --- | ---: | ---: | ---: |
| study_workload | 4 | 1 | 0 |
| employment_prospects | 8 | 2 | 0 |
| starting_salary | 4 | 1 | 0 |
| work_life_balance | 4 | 1 | 0 |
| digital_nomadism | 4 | 1 | 0 |
| department_itself | 0 | 0 | 1 |
| academic_curriculum | 0 | 0 | 1 |
| student_life | 0 | 0 | 1 |
| internships | 0 | 0 | 3 |
| graduate_studies | 0 | 0 | 1 |
| common_concerns | 0 | 0 | 3 |

## Evidence for each source addition

### retrieval_paraphrase_cases.json

- **q013** (+`src_099`; previously unsourced): src_099 reports a 2011 US NSSE survey: engineering seniors studied about 19 hours weekly, versus 15 for all full-time students. This is a dated engineering-wide benchmark, not a measured Computer Engineering or OSTIM average.
- **q016** (+`src_103`; previously unsourced): src_103 reports Turkish 2025 ICT graduate registered employment of 76.7% and mean time to first job of 11.4 months. These broader-field statistics support a qualified employment-prospects answer, not a claim that hiring is easy or a CENG-specific placement rate.
- **q017** (+`src_095`): src_095 projects US software-developer employment growth of 10.2% and data-scientist growth of 34.6% over 2025-2035; this supports a qualified outlook, not an AI-proof career guarantee.
- **q019** (+`src_097`): src_097 names software, energy, electrical/electronic materials and IT consulting as sectors employing software engineers; these are examples for the software career route, not an exhaustive list for all CENG graduates.
- **q021** (+`src_096`, `src_101`, `src_102`): src_096 reports fully remote and hybrid Turkish developer survey respondents; src_101 reports remote tech workers; src_102 identifies IT among digital-nomad professions. These establish remote software/IT routes, not remote eligibility for every hardware role.
- **q024** (+`src_116`): src_116 Article 5(b)(2) describes entrepreneurship guidance for becoming an entrepreneur; Article 10(7) describes mentoring, funding connections and free pre-incubation space. This supports the OSTIM student entrepreneurship route, without guaranteeing business success.
- **q026** (+`src_095`; previously unsourced): src_095 projects US software developers from 1,717.8 thousand jobs in 2025 to 1,892.6 thousand in 2035, and data scientists from 275.6 to 371.0 thousand. These are occupation-specific US forecasts, not a guarantee of sufficient jobs for every graduate or a Turkish forecast.
- **q029** (+`src_058`, `src_111`, `src_117`): src_058 Article 32 requires at least 2.00 GPA to graduate and provides completion exams below that threshold; src_117 Article 10 describes those exams. src_111 Article 5 allows undergraduate GPA to enter graduate admission assessment and requires 3.00 for direct-entry doctoral applicants. These are OSTIM academic consequences, not employer rejection guarantees.
- **q031** (+`src_096`, `src_097`; previously unsourced): src_096 gives 2025 Turkish junior software-role salary averages, including full-stack 50,500 TL and front-end 46,500 TL monthly. src_097 gives a 0-1-year software-engineer average of 39,000 TL, explicitly based on applicant net salary expectations. These answer the Turkey/software route only: neither is a worldwide or all-CENG-graduate starting-salary average.
- **q041** (+`src_109`): src_109 Article 1 explains workplace learning benefits: applying theory, understanding production/service processes, work discipline and professional experience. Its applied courses are explicitly distinct from statutory internships.
- **q042** (+`src_109`, `src_110`, `src_116`): src_109 Article 11(4) describes university-found workplaces and approval of student-found alternatives; src_110 clause 5 requires students to find companies for the optional Career Experience Program. src_116 Article 10(6) describes KARPİEM internship information, application/interview training and career fairs.
- **q045** (+`src_104`): src_104 Article 9 provides project-idea competition support for eligible national/international scientific or social entrepreneurship competitions. This gives an OSTIM-specific benefit of eligible competitions, not a promise that every hackathon qualifies.
- **q052** (+`src_095`): src_095 gives comparable US 2025-2035 growth forecasts: data scientists 34.6%, computer/information systems managers 15.8%, software developers 10.2%. It supports comparison of these listed routes, not a comprehensive ranking of every CENG specialization.
- **q053** (+`src_100`, `src_101`; previously unsourced): src_100 reports 38% of surveyed engineering leaders working longer hours and work encroaching on personal time; src_101 reports burnout differences by role, company size and work setup. These support a variable, qualified work-life-balance answer rather than a universal good/bad rating.
- **q054** (+`src_100`, `src_101`): src_100 reports burnout among 617 engineering leaders/developers and workload after layoffs; src_101 reports 44.67% significant burnout and high burnout in hardware/infrastructure roles. These are survey findings, not a claim that every engineer is stressed.
- **q055** (+`src_102`; previously unsourced): src_102 explicitly describes combining remote work with travel across countries and lists information technology among main digital-nomad professions. Employer policies, legal/tax compliance and location-independent duties remain constraints.

### unseen_coverage_cases.json

- **department_itself_008** (+`src_107`; previously unsourced): src_107 Article 6(3) sets at least 60/100 on the university English proficiency exam; Article 6(6)-(9) gives alternative exemption routes. Do not confuse proficiency with the placement test.
- **academic_curriculum_002** (+`src_105`, `src_106`): src_105 Article 14(ğ) refers to the second-major diploma; src_106 Article 14(l)-(m) explicitly says a minor gives only a certificate, not a diploma or degree rights.
- **academic_curriculum_003** (+`src_105`; previously unsourced): src_105 Article 8(b)-(c) requires at least 70/100 (2.72/4.00), successful completion of prior courses and top-20% standing or the stated entry-score alternative. Other eligibility restrictions also apply; GPA alone is insufficient.
- **academic_curriculum_009** (+`src_116`): src_116 Article 7(3)-(5) explicitly requires advisor approval in both initial registration and add/drop periods; unapproved registration is invalid even if paid.
- **student_life_008** (+`src_120`; previously unsourced): src_120 says to complete the provided form for face-to-face or online counseling, gives weekday 08:30-17:30 availability, the F Block fifth-floor PDR office and email contacts for requests.
- **internships_006** (+`src_109`): src_109 defines the applied-training file and evaluation form; Articles 9 and 11 describe mentor approval, daily records, signed attendance documentation and the closed-envelope evaluation.
- **internships_008** (+`src_110`; previously unsourced): src_110 clause 1 explicitly states that the university has no compulsory internship process; clauses 2 and 6 describe an optional 20-working-day Career Experience Program. Correct the premise rather than presenting 20 as compulsory summer internship days; applied Workplace Experience is a separate requirement.
- **internships_009** (+`src_110`; previously unsourced): src_110 clause 11 assigns 20-working-day insurance registration to university Human Resources; clause 16 describes SGK processing. The appended student undertaking requires reimbursement of university expenses connected with voluntary internship, so registration must not be represented as an unconditional promise that the university bears every cost.
- **internships_010** (+`src_110`; previously unsourced): src_110 clause 1 corrects the compulsory-internship premise; clause 14 leaves online/remote Career Experience to the faculty, and clause 8 gives conditional recognition toward the following Workplace Experience. There is no blanket remote-internship approval.
- **graduate_studies_002** (+`src_111`): src_111 Articles 23-25 describe scientific research, graduate coursework, seminar, thesis and oral defense, rather than merely more undergraduate classes.
- **graduate_studies_003** (+`src_111`): src_111 Articles 23-27 distinguish research-oriented thesis study from professional-depth non-thesis study with a term project.
- **graduate_studies_004** (+`src_116`): src_116 Articles 4(i), 5(a)(2) and 10(2)(a),(c) assign academic advisors course-selection, study-planning and career guidance duties; it identifies whom an OSTIM undergraduate can approach, not a guaranteed graduate-admission course list.
- **graduate_studies_007** (+`src_111`; previously unsourced): src_111 Article 5(1) sets a thesis-master admission ALES floor of 55 in the relevant score type and allows the Senate to set the actual threshold. This is a university-wide minimum, not confirmation of the current CENG intake cutoff.
- **common_concerns_002** (+`src_104`; previously unsourced): src_104 Article 5(1)(a)-(d) sets scholarship durations and says awards remain valid during those periods regardless of achievement or registration; extra prep time counts, justified frozen registration does not. Article 4(14) separately imposes GPA and other conditions for the annual academic-achievement discount; Article 7 separately addresses international awards.
- **common_concerns_003** (+`src_104`, `src_107`; previously unsourced): src_107 Articles 5 and 10 allow up to two prep years, describe the repeat-year/proficiency route after one unsuccessful year, and termination after two unsuccessful years with three later exam rights on request. src_104 Article 5 says extra unsuccessful prep time consumes scholarship duration.
- **common_concerns_004** (+`src_115`; previously unsourced): src_115 Articles 6(f), 7(a) and 8 provide necessary extra time, accessible/separate exam arrangements and a decision route for needs not explicitly listed. Dyslexia-specific minutes or automatic entitlement are not specified; individual arrangements require the relevant unit.
- **common_concerns_009** (+`src_116`): src_116 Articles 7 and 10(2)(a) identify advisor course-selection and study-planning duties; the explicit reduced-load permission and 12-ECTS minimum remain in src_058 Article 19.

## Unfilled gaps rechecked

### Paraphrase

- **q023**: No answering source: src_095 ranks projected US job growth, not current demand across all CENG specializations; salary and workforce-profile surveys do not establish the highest-demand specialty.
- **q025**: No answering source: src_100 describes layoffs and src_103 gives broader Turkish graduate employment indicators, but neither compares CENG graduate supply with vacancies to establish market saturation.
- **q032**: No answering source: src_096 compares selected Turkish software roles and src_097 compares software-sector salaries, but neither establishes the highest-paid specialization across Computer Engineering in Turkey.
- **q033**: No answering source: src_098 gives average coding experience by developer role and src_097 gives salaries by experience band; neither states the time required to reach senior software engineer.

### Unseen

- **academic_curriculum_004**: No answering source: src_106 sets minor rules and annual quota announcements but does not list the minors currently open to CENG students.
- **academic_curriculum_010**: No answering source for an actual weekly timetable: src_107 Article 8 specifies at least 20 class hours weekly, determined by level, but no normal day-by-day prep schedule is present.
- **student_life_005**: No answering source: src_112 governs how clubs are formed and run but does not name current coding or robotics clubs.
- **student_life_006**: No answering source for first-year access after 19:00: src_114 requires unit planning, approval for unplanned use and locked labs outside use; it supplies no evening opening schedule or first-year access entitlement.
- **student_life_007**: No answering source for monthly dorm prices: src_123 lists partner dormitories and free viewing/information services, not accommodation charges.
- **graduate_studies_008**: No answering source for an IELTS or TOEFL score: src_111 Article 5(4) mentions accepted equivalents and a YDS/IYS minimum, while src_107 delegates equivalent exam scores; neither gives IELTS/TOEFL conversion thresholds.
- **graduate_studies_009**: No answering source for an available paid CENG assistantship and its stipend: src_104 Article 4(3)(c) waives tuition for university research assistants, src_118 regulates separate part-time student jobs, and src_125 sets general staff pay principles; none publishes the requested vacancy or amount.
- **graduate_studies_010**: No answering source: src_111 contains general doctoral regulations, not a current list establishing that a separate CENG PhD is running.
- **common_concerns_001**: No answering source for next-year tuition as of this review (2026-10-20): src_108 gives 2026-2027 annual English CENG fees (1,250,000 TL full, 625,000 TL at 50%), not 2027-2028 fees or a guaranteed full-degree total. A dated price must not be relabeled as a future fee.
- **common_concerns_005**: No answering source for a laptop-loan scheme: src_119 offers means-tested financial/social assistance and src_114 regulates on-campus labs, but neither states that students can borrow a laptop.

Other unchanged questions were also compared with the available texts; none gained a direct answering passage. No new source establishes cohort size, accreditation, career-center booking, prescribed first-year laptop/IDE, yearly FPGA-elective availability, named recent graduate employers, guaranteed job offers, OSTIM-specific six-month employment, German job-language levels, Turkish work-permit fees, current Ankara vacancies, undergraduate quantum/GPU access, future dominant programming languages, or a ChatGPT homework policy.

Validation: both JSON files parse; all 360 rows and non-label fields are preserved; old sources are retained; added IDs are unique, allowed and backed by existing processed text. Paraphrase variants retain consistent labels and notes within each original-question group.
