# Unresolved Source Impact

## Scope

This document evaluates the 11 approved sources that remain unresolved after Stage 8B.

No replacement sources were collected. No preprocessing, cleaning, chunking, embeddings, ChromaDB, Ollama, RAG, chatbot, frontend, or backend work was performed.

## Summary

- **Total unresolved sources:** 11
- **Critical unresolved sources:** 0
- **Important unresolved sources:** 8
- **Supplementary unresolved sources:** 3

No unresolved source is classified as Critical because the locally available corpus already contains overlapping evidence for every major university-required knowledge area. Some unresolved sources are still Important because they would improve authority, detail, or balance in specific answers.

## Impact Table

| Source ID | Title | Categories/questions supported | Acquisition problem | Importance | Overlapping local evidence | Recommendation |
|---|---|---|---|---|---|---|
| src_009 | Curricula Recommendations | Curriculum; Q1-Q6, Q8, Q60 | HTTP 403 Forbidden | Important | OSTIM curriculum/course pages `src_003`, `src_004`; OSTIM department pages `src_001`, `src_002`; ACM/Linux/OECD sources already local for broader skills context | Manually save the ACM page if browser access works. Corpus can proceed without it because official OSTIM curriculum evidence is local. |
| src_010 | Software Developers, Quality Assurance Analysts, and Testers | Career opportunities, employment, salaries; Q17, Q19, Q22, Q26, Q31 | HTTP 403 Forbidden | Important | O*NET `src_014`, Turkey ICT sources `src_025`, `src_026`, OECD digital/Türkiye PDFs `src_045`, `src_046`, Stack Overflow/JetBrains `src_049`, `src_051` | Manually save from BLS browser page if possible. Not blocking because local sources cover software career and ICT demand. |
| src_011 | Computer Hardware Engineers | Hardware careers, programming relevance, salaries; Q6, Q19, Q22, Q31, Q50 | HTTP 403 Forbidden | Important | O*NET hardware engineers `src_014`, OSTIM curriculum/research `src_003`, `src_004`, `src_008`, UI/skills sources | Manually save if possible. Not blocking because O*NET and OSTIM sources cover hardware tasks and curriculum. |
| src_012 | Information Security Analysts | Cybersecurity; Q22, Q23, Q35, Q38, Q52 | HTTP 403 Forbidden | Important | Linux Foundation `src_016`, ITA Türkiye ICT `src_026`, WEF `src_017`, OSTIM research `src_008`, JetBrains `src_051` | Manually save if possible. Not blocking because cybersecurity is still represented by local industry and ICT sources. |
| src_013 | Computer and Information Research Scientists | Graduate studies, AI/research careers, salaries; Q34, Q46-Q48 | HTTP 403 Forbidden | Important | MIT graduate guidance `src_044`, OECD skills-first `src_031`, OSTIM research `src_008`, WEF `src_017`, DORA/AI sources `src_052`, `src_053` | Manually save if possible. Not blocking because graduate-study decision evidence is local. |
| src_032 | Working anytime, anywhere: The quality of working time in the EU | Work-life balance, remote work; Q21, Q53-Q55 | HTTP 429 Too Many Requests | Important | ILO work-life balance `src_019`, Stack Overflow developer work data `src_049`, `src_050`, JetBrains `src_051`, student wellbeing `src_054` | Manually download official Eurofound PDF or save HTML later. Not blocking because work-life/remote evidence exists locally. |
| src_042 | Curricular Guidance | Common misconceptions and computing discipline distinctions; Q4-Q6, Q50, Q56, Q60 | HTTP 200 content failed integrity check as likely bot/error page | Important | OSTIM department/curriculum `src_001`, `src_003`, `src_004`; NCWIT `src_040`, `src_041`; ACM source `src_009` remains unresolved but broad discipline evidence exists elsewhere | Manually save browser HTML if public page renders correctly. Not blocking because OSTIM and misconception sources are local. |
| src_043 | Subdisciplines | Specialization choice; Q23, Q38, Q49, Q51, Q52 | HTTP 200 content failed integrity check as likely bot/error page | Important | OSTIM research `src_008`, Linux Foundation `src_016`, WEF `src_017`, ITA `src_026`, JetBrains `src_051`, DORA `src_052` | Manually save if browser page loads. Not blocking because local sources still cover AI, cybersecurity, ICT, and technology trends. |
| src_047 | Education GPS - Türkiye - Overview of the education system (EAG 2025) | Türkiye graduate education/employment and women/ICT context; Q16, Q31, Q46, Q48, Q58 | HTTP 403 Forbidden | Supplementary | TURKSTAT `src_021`, `src_022`, `src_023`, `src_024`; OECD Türkiye survey `src_046`; EIGE/Eurostat gender dataset `src_048` | Manual browser save if needed. Supplementary because stronger local Turkey employment and gender evidence already exists. |
| src_055 | Investigating Academic Confidence, Workload Stress, and Performance in a BlendFlex Computer Science Course | Student workload/stress, beginner success; Q11-Q13, Q54, Q59 | HTTP 403 Forbidden | Supplementary | Springer student wellbeing `src_054`, Brown beginner guidance `src_039`, Stack Overflow/JetBrains developer stress context `src_050`, `src_051` | Manually save official ACM landing page or legal PDF if available. Supplementary because the broader student wellbeing article is local. |
| src_056 | How Beginning Programmers and Code LLMs (Mis)read Each Other | Beginner programming, math misconceptions, AI-assisted coding; Q9, Q12, Q18, Q36, Q57, Q59 | HTTP 403 Forbidden | Supplementary | Brown beginner guidance `src_039`, GitHub Docs `src_015`, DORA AI sources `src_052`, `src_053`, Springer wellbeing `src_054` | Manually save official ACM landing page or legal PDF if available. Supplementary because beginner and AI evidence remains local. |

## Coverage Impact

The unresolved sources would improve depth and citation quality, but their absence does not remove any major knowledge-base area. The local corpus still contains:

- official OSTIM department and curriculum evidence;
- Turkey employment, ICT, salary-context, and gender evidence;
- AI, cybersecurity, skills, Git, Linux, and future-technology evidence;
- internship and career-readiness evidence;
- graduate study and international-career evidence;
- work-life, remote work, student wellbeing, and misconception evidence.

## Recommendation

Proceeding to preprocessing is reasonable with the current 45-source local corpus, while keeping the 11 unresolved sources documented for optional later manual acquisition.
