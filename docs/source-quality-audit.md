# Source Quality Audit

## Scope

This audit reviews the 44 accepted source records in `knowledge_base/sources.json`.

No sources were deleted. No new sources were collected. No source metadata was modified during this audit.

## Overall Quality Finding

The current source set is generally strong and aligned with the WEX428 guideline. It includes official OSTIM Technical University sources, official curriculum/course pages, professional computing organizations, government and labor data, technical documentation, industry reports, international organizations, and university career-guidance resources.

The main quality risks are not fake or unreliable sources. The main risks are:

- sources being used beyond their geographic scope,
- sector-level salary evidence being treated as Computer Engineering salary evidence,
- general career guidance being treated as employer outcome data,
- missing exact publication dates for active official pages,
- and near-overlap among some career-readiness sources.

## Duplicate and Near-Duplicate Review

| Source IDs | Issue | Assessment | Action recommended |
|---|---|---|---|
| src_009, src_042 | Both are ACM computing/curricular guidance sources. | Near-overlap, but not a harmful duplicate. src_009 covers ACM curricula broadly; src_042 helps with computing subdiscipline misconceptions. | Keep both, but cite carefully by purpose. |
| src_018, src_037 | Both are NACE internship sources. | Not duplicates. src_018 is student perception of internship importance; src_037 is employer-side intern hiring and selection evidence. | Keep both. |
| src_033, src_034, src_037 | NACE employer/hiring evidence appears across several records. | Near-overlap but useful because each supports a different claim: GPA/skills, new-grad readiness, internships. | Keep all; avoid using NACE as the only employer source in final answers. |
| src_010, src_014 | Both discuss computer hardware/software-related occupational work. | Complementary. BLS provides labor outlook and pay; O*NET provides structured tasks, tools, and work context. | Keep both. |
| src_019, src_032 | Both support remote/work-life balance. | Complementary. ILO is global and broad; Eurofound is EU-specific and current. | Keep both, but label geographic scope. |

## Authority Review

| Source group | Authority level | Notes |
|---|---|---|
| Official OSTIM sources, src_001-src_008 | High | Best evidence for local department, curriculum, staff, workplace documents, and research. |
| ACM, SFIA, NCWIT, NACE | High | Professional/educational organizations suitable for computing education, career readiness, and misconception evidence. |
| BLS, O*NET, TURKSTAT, European Commission, Europass, SBA | High | Government or official public sources suitable for labor, career, recognition, mobility, and business guidance. |
| WEF, OECD, ILO, Eurofound | High | Recognized international institutions for future work, skills, labor, and work-life balance. |
| Linux Foundation, TÜBİSAD, ITA, Türkiye Investment Office | Moderate to High | Useful industry/sector evidence. Should be interpreted as sector/trend evidence, not direct student outcome evidence. |
| MIT, Berkeley, Brown, UIUC career/advising pages | High for guidance | Strong for advising and education context; not primary labor statistics. |

## Metadata Issues

| Issue | Affected sources | Risk | Recommendation |
|---|---|---|---|
| Missing exact publication/update dates | src_001-src_009, src_014-src_016, src_019-src_020, src_025, src_027-src_028, src_030, src_035-src_036, src_038, src_040-src_044 where exact dates are not visible | Some recency claims must be cautious. | Keep `publication_date: null` unless a real date is verified. Mention visible year/update notes in `notes`. |
| `raw_file_path` is null | All accepted sources | Expected for planning/source registry because raw acquisition has not started. | Populate later during content acquisition/download or manual archiving. |
| Secondary categories stored in `notes` | Many sources | Later preprocessing may need structured multi-category filtering. | Consider a future schema version with `categories` array, but do not change during this audit. |
| English/Turkish mix | Multiple sources | Not a problem, but language-aware preprocessing will matter later. | Preserve language metadata and consider translation/embedding language strategy later. |

## Category Assignment Review

No clearly incorrect primary category assignment was found. Several sources have broad relevance that exceeds their primary category:

- src_021 supports both Employment and Salaries.
- src_026 supports Employment, AI, Cybersecurity, Future Technologies, and Remote Work.
- src_031 supports Skills, Employment, Career Opportunities, and Graduate Studies.
- src_034 supports Skills, Employment, Internships, and Student Life.
- src_042 supports Common Misconceptions, Department Information, Curriculum, and Career Opportunities.

This is acceptable because the current schema has one primary `category` field and secondary relevance in `notes`.

## Geographic Limitations

| Source IDs | Geographic limitation | Risk |
|---|---|---|
| src_010-src_014 | U.S. labor/occupation data | Should not be presented as Turkey employment or salary data. |
| src_018, src_033, src_034, src_037 | Mostly U.S. employer/student survey evidence | Useful for general employability, but not proof of Turkish employer behavior. |
| src_019 | Global work-life evidence | Useful broadly, but not software- or Turkey-specific. |
| src_028-src_030 | Europe/international recognition and mobility | Useful for working abroad, but not personalized immigration/legal advice. |
| src_032 | EU work-life/remote-work evidence | Should not be generalized to Turkey without caution. |
| src_040 | U.S.-focused women-in-computing data | Useful for misconception framing, but not Turkey participation data. |

## Time-Sensitive Evidence Risks

| Topic | Risk | Current status |
|---|---|---|
| Salaries | Salary figures become outdated quickly and vary by country, occupation, city, seniority, and currency. | Turkey salary evidence is only sector/field-level and must remain cautious. |
| Job demand | AI, cybersecurity, software, and cloud demand changes quickly. | Current evidence is recent, but Turkey occupation-level demand remains weak. |
| AI impact | Claims about AI replacing engineers can become speculative. | Current evidence supports transformation/reskilling, not simple replacement claims. |
| Remote work | Regulations and employer policies vary by country and change often. | Current evidence supports general remote-work/work-life considerations, not legal/tax advice. |

## Sources Most at Risk of Overextension

| Source ID | Risk if misused | Safe use |
|---|---|---|
| src_023 | Treating sector labor cost as Computer Engineering salary. | Use only as Turkey Information and Communication sector wage/labor-cost context. |
| src_024 | Treating 2022 earnings as current salary. | Use as historical official earnings context with date caveat. |
| src_025 | Treating investment-promotion data as neutral graduate employment data. | Use as ICT sector overview, not graduate placement proof. |
| src_027 | Treating report landing page as full report evidence. | Use only for identifying the existence/scope of the TÜBİSAD 2024 report unless the full report is later acquired. |
| src_031 | Treating skills-first labor market as proof GPA never matters. | Use to support skills recognition and professional development, not to dismiss credentials. |
| src_036 | Treating Berkeley GPA advice as a universal rule. | Use as university career guidance, not an employer law. |
| src_038 | Treating SFIA levels as years-to-senior timeline. | Use for responsibility growth, not fixed promotion timing. |
| src_029 | Treating EU Blue Card information as legal advice. | Use for general work-abroad considerations only. |

## Outdated Source Review

No accepted source appears unacceptable solely due to age. However:

- src_024 uses 2022 salary/earnings data and should be retained only as official historical context.
- Some official OSTIM pages and guidance pages have no exact publication date; they appear current but should be rechecked before final submission.
- Future technology and AI sources are recent enough for the current stage but should be refreshed if the project timeline extends close to defense.

## Broken or Inconsistent Metadata Review

No structural JSON errors were found in the current source registry. The source IDs are sequential from `src_001` to `src_044`.

Potential future improvements:

- Add a `categories` array in a future schema version.
- Add `geographic_scope`.
- Add `measurement_year` for salary/employment sources.
- Add `accepted_batch`.
- Add `last_verified`.

These are recommendations only; the schema should not be changed during this audit unless the user requests it.

## Source Quality Conclusion

The accepted sources are broadly reliable, but the future RAG system must preserve source limitations in retrieved context and final answers. The biggest risk is overconfident advisory language for salary, GPA, internships, AI replacement, specialization ranking, and Turkey-specific outcomes.
