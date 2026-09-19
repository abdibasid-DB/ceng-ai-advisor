# Source Collection Batch 03

## Stage

Source Collection - Batch 3: Turkey Employment, Salaries, International Careers, and Remaining Career Evidence

## Project

AI-Powered Computer Engineering Student Advisor

## Date Accessed

2026-08-30

## Scope

This batch focuses on Turkey-specific labor-market evidence, cautious salary evidence, international career and qualification-recognition evidence, career progression, remote work, work-life balance, and remaining career evidence gaps.

No preprocessing, chunking, embeddings, ChromaDB, Ollama, RAG pipeline, chatbot logic, frontend features, backend features, or application functionality were implemented in this stage.

## Collection Rules Applied

- Accepted only real and verifiable sources.
- Prioritized official Turkish government statistics, official sector/government pages, recognized international institutions, and reputable professional/industry organizations.
- Treated salary evidence carefully and rejected unverifiable salary websites.
- Used `null` for missing exact publication dates rather than inventing dates.
- Recorded limitations where evidence is sector-level, country-level, or international rather than Computer Engineering-specific.
- Did not make immigration, salary, or job-market claims beyond what the source can support.

## Accepted Sources

### src_021

- **Title:** Higher Education Employment Indicators, 2025
- **Organization:** Turkish Statistical Institute (TURKSTAT / TÜİK)
- **Source type:** Government employment statistics
- **URL:** https://veriportali.tuik.gov.tr/en/press/58027
- **Publication/update date:** 2026-07-23
- **Category/categories:** Employment; secondary: Salaries, Graduate Studies, Career Opportunities
- **Country/geographic scope:** Türkiye
- **Questions/topics supported:** Which higher-education fields have stronger employment indicators? How quickly do graduates enter work? Is ICT-related higher education employable in Türkiye?
- **Why selected:** This is the strongest official source found for Turkey-specific graduate employment indicators by higher-education field/programme.
- **Reliability assessment:** High. Official TURKSTAT release using administrative registers matched in the Education-Labour Force Database.
- **Recency assessment:** Strong. Published in 2026 for 2025 indicators.
- **Important limitations:** The inspected public text gives field/programme indicators and rankings but does not provide a full Computer Engineering salary table.
- **Employment/salary measurement note:** Geographic scope: Türkiye. Measurement year: 2025. Measures registered employment, first-job duration, field alignment, and monthly average earnings indicators for higher-education graduates.

### src_022

- **Title:** Labour Force Statistics, 2025
- **Organization:** Turkish Statistical Institute (TURKSTAT / TÜİK)
- **Source type:** Government labor statistics
- **URL:** https://veriportali.tuik.gov.tr/Bulten/Index?dil=2&p=Labour-Force-Statistics-2025-57996
- **Publication/update date:** 2026-03-25
- **Category/categories:** Employment
- **Country/geographic scope:** Türkiye
- **Questions/topics supported:** What is the broader Turkish labor-market context for employment, unemployment, youth unemployment, labor-force participation, and sector distribution?
- **Why selected:** Computer Engineering employment questions need national labor-market context before interpreting ICT-specific evidence.
- **Reliability assessment:** High. Official annual TURKSTAT labor-force statistics.
- **Recency assessment:** Strong. Published in 2026 for 2025 statistics.
- **Important limitations:** Not specific to Computer Engineering, software, or ICT occupations.
- **Employment measurement note:** Geographic scope: Türkiye. Measurement year: 2025. Measures national labor-force, employment, and unemployment indicators.

### src_023

- **Title:** Labour Cost Statistics, 2024
- **Organization:** Turkish Statistical Institute (TURKSTAT / TÜİK)
- **Source type:** Government salary/labor-cost statistics
- **URL:** https://veriportali.tuik.gov.tr/en/press/54011
- **Publication/update date:** 2025-12-25
- **Category/categories:** Salaries; secondary: Employment
- **Country/geographic scope:** Türkiye
- **Questions/topics supported:** What official salary-adjacent evidence exists for Türkiye's Information and Communication sector?
- **Why selected:** It is official, recent, and includes sector-level labor cost, gross wage, and gross earnings information.
- **Reliability assessment:** High. Official TURKSTAT labor-cost statistics.
- **Recency assessment:** Strong. Published in 2025 for 2024 data.
- **Important limitations:** Labor cost and gross earnings by sector are not the same as a Computer Engineering salary. It should be used carefully as sector context, not as a direct salary answer.
- **Salary measurement note:** Geographic scope: Türkiye. Measurement year: 2024. Occupation/category: Information and Communication sector. Measures monthly average labor cost, gross wage, and gross earnings. Currency: TRY.

### src_024

- **Title:** Structure of Earnings Statistics, 2022
- **Organization:** Turkish Statistical Institute (TURKSTAT / TÜİK)
- **Source type:** Government salary statistics
- **URL:** https://veriportali.tuik.gov.tr/en/press/49750
- **Publication/update date:** 2023-12-25
- **Category/categories:** Salaries; secondary: Employment
- **Country/geographic scope:** Türkiye
- **Questions/topics supported:** How do earnings vary by education, economic activity, occupation group, and sex in Türkiye?
- **Why selected:** It provides official earnings evidence with methodology and administrative data notes.
- **Reliability assessment:** High. Official TURKSTAT earnings statistics.
- **Recency assessment:** Acceptable but older than ideal for salary questions. Retained because it is authoritative and transparent, and no better occupation-specific official Computer Engineering salary source was verified in this batch.
- **Important limitations:** Reference year is 2022 and the source is not specific to Computer Engineering. It should not be used as a current direct salary claim.
- **Salary measurement note:** Geographic scope: Türkiye. Reference year: 2022. Occupation/category: broad economic activity, education, and occupation groups. Measures monthly and annual gross wages/earnings. Currency: TRY.

### src_025

- **Title:** ICT
- **Organization:** Presidency of the Republic of Türkiye Investment Office
- **Source type:** Official sector profile
- **URL:** https://www.invest.gov.tr/en/sectors/pages/ict.aspx
- **Publication/update date:** null
- **Category/categories:** Employment; secondary: Career Opportunities, Future Technologies, Entrepreneurship
- **Country/geographic scope:** Türkiye
- **Questions/topics supported:** How large is Türkiye's ICT sector? Are there ICT companies, employees, R&D centers, and graduates? What areas of digital growth exist?
- **Why selected:** It is an official Türkiye sector overview and complements TURKSTAT with market and workforce context.
- **Reliability assessment:** High for official sector-positioning information. It should still be interpreted as an investment-promotion page.
- **Recency assessment:** Good. The inspected page includes 2024 sector indicators, but no exact page publication date was visible.
- **Important limitations:** Not a neutral statistical press release, and not Computer Engineering graduate-specific.
- **Employment measurement note:** Geographic scope: Türkiye. Measurement year visible for some indicators: 2024. Occupation/category: ICT sector and related workforce indicators.

### src_026

- **Title:** Turkey - Information and Communication Technology
- **Organization:** International Trade Administration, U.S. Department of Commerce
- **Source type:** Government country commercial guide
- **URL:** https://www.trade.gov/knowledge-product/turkey-information-and-communication-technology
- **Publication/update date:** 2026-01-29
- **Category/categories:** Employment; secondary: Career Opportunities, Future Technologies, Artificial Intelligence, Cybersecurity, Remote Work
- **Country/geographic scope:** Türkiye
- **Questions/topics supported:** What is the state of Türkiye's ICT market? Which technology areas are growing? What opportunities exist in software, cloud, AI, cybersecurity, IoT, 5G, and data centers?
- **Why selected:** It gives a current external-government view of Türkiye's ICT sector and technology opportunities.
- **Reliability assessment:** High. Official U.S. government country commercial guide.
- **Recency assessment:** Strong. Last published in 2026.
- **Important limitations:** Commercial guide rather than primary Turkish statistical data; should be cross-checked with Turkish official and industry sources.
- **Employment measurement note:** Geographic scope: Türkiye. Measurement years include recent ICT market data and 2025 projections. Occupation/category: ICT sector, IT employment, software, cloud, AI, cybersecurity, and related markets.

### src_027

- **Title:** TÜBİSAD 2024 Bilgi ve İletişim Teknolojileri Sektörü Pazar Verileri ve Trendleri Raporu
- **Organization:** TÜBİSAD Bilişim Sanayicileri Derneği
- **Source type:** Industry report page
- **URL:** https://www.tubisad.org.tr/tr/bilgi-bankasi/detay/TUBISAD-2024-Bilgi-ve-Iletisim-Teknolojileri-Sektoru-Pazar-Verileri-ve-Trendleri-Raporu/49/5160/0
- **Publication/update date:** null
- **Category/categories:** Employment; secondary: Career Opportunities, Skills and Technologies, Future Technologies
- **Country/geographic scope:** Türkiye
- **Questions/topics supported:** What does the Turkish ICT industry report as sector trends and market context?
- **Why selected:** TÜBİSAD is a relevant Turkish ICT industry association, and the page identifies its 2024 ICT sector market data and trends report.
- **Reliability assessment:** Good as industry evidence. It should be paired with official statistics where possible.
- **Recency assessment:** Good. Report year is 2024, but no exact publication date was visible in the inspected text.
- **Important limitations:** The inspected landing page provides limited methodology text without relying on the full report content in this batch.
- **Employment measurement note:** Geographic scope: Türkiye. Measurement/report year: 2024. Occupation/category: ICT sector market and trends.

### src_028

- **Title:** Preparing for work abroad
- **Organization:** Europass, European Union
- **Source type:** Official international career guidance
- **URL:** https://europass.europa.eu/en/work-europe/preparing-work-abroad
- **Publication/update date:** null
- **Category/categories:** Remote Work; secondary: Employment, Career Opportunities, Graduate Studies
- **Country/geographic scope:** Europe / international mobility
- **Questions/topics supported:** Can Computer Engineering graduates work abroad? How should students prepare documents, qualifications, CVs, diplomas, and recognition checks?
- **Why selected:** It gives official practical guidance for employment mobility and qualification presentation in Europe.
- **Reliability assessment:** High. Official Europass/EU guidance.
- **Recency assessment:** Acceptable. Active official guidance, but no exact publication date was visible.
- **Important limitations:** Does not guarantee employment abroad or immigration eligibility. It is preparation guidance, not legal advice.

### src_029

- **Title:** EU Blue Card
- **Organization:** European Commission - Migration and Home Affairs
- **Source type:** Official immigration information
- **URL:** https://home-affairs.ec.europa.eu/policies/migration-and-asylum/eu-immigration-portal/eu-blue-card_en
- **Publication/update date:** 2025-04-01
- **Category/categories:** Remote Work; secondary: Employment, Career Opportunities
- **Country/geographic scope:** European Union
- **Questions/topics supported:** What official route exists for highly qualified non-EU workers? What considerations exist around job offers, higher professional qualifications, applications, and national rules?
- **Why selected:** International-career questions can involve legal work authorization, so an official source is necessary.
- **Reliability assessment:** High. Official European Commission migration page.
- **Recency assessment:** Strong. Page update date is 2025-04-01.
- **Important limitations:** Immigration eligibility depends on the destination country and personal circumstances. The future advisor must avoid personalized legal advice.

### src_030

- **Title:** Türkiye
- **Organization:** ENIC-NARIC Networks
- **Source type:** Official qualification recognition profile
- **URL:** https://www.enic-naric.net/page-Turkiye
- **Publication/update date:** null
- **Category/categories:** Graduate Studies; secondary: Employment, Remote Work
- **Country/geographic scope:** Türkiye / international recognition
- **Questions/topics supported:** How are Turkish higher-education qualifications documented and recognized? What bodies are responsible? How do recognition systems affect international study or work preparation?
- **Why selected:** Degree recognition and qualification transparency are important for working or studying abroad.
- **Reliability assessment:** High. ENIC-NARIC is the official network for recognition information.
- **Recency assessment:** Good. Page states it was last updated in 2026, but no exact date was visible.
- **Important limitations:** Destination-country recognition and professional regulation still matter; not a job guarantee.

### src_031

- **Title:** A Skills-First Labour Market
- **Organization:** Organisation for Economic Co-operation and Development (OECD)
- **Source type:** Recognized international report
- **URL:** https://www.oecd.org/en/publications/a-skills-first-labour-market_2e1b85f0-en.html
- **Publication/update date:** 2026-06-18
- **Category/categories:** Skills and Technologies; secondary: Employment, Career Opportunities, Graduate Studies
- **Country/geographic scope:** International / OECD
- **Questions/topics supported:** Do skills matter compared with grades or credentials? How should students think about personal projects, professional development, lifelong learning, and career progression?
- **Why selected:** It gives credible evidence for skills-first hiring and professional development without inventing a fixed career-progression timeline.
- **Reliability assessment:** High. OECD publication with DOI.
- **Recency assessment:** Strong. Published in 2026.
- **Important limitations:** International labor-market guidance, not Computer Engineering-only and not Turkey-specific.

### src_032

- **Title:** Working anytime, anywhere: The quality of working time in the EU
- **Organization:** Eurofound
- **Source type:** Recognized international report
- **URL:** https://www.eurofound.europa.eu/default/publications/all/working-anytime-anywhere-the-quality-of-working-time-in-the-eu
- **Publication/update date:** 2026-07-21
- **Category/categories:** Work-Life Balance; secondary: Remote Work, Employment
- **Country/geographic scope:** European Union
- **Questions/topics supported:** Can remote work improve or harm work-life balance? What are the risks of autonomy, long hours, and boundary blurring?
- **Why selected:** Remote work and work-life balance need evidence beyond anecdotal software-industry opinions.
- **Reliability assessment:** High. Eurofound is an EU agency.
- **Recency assessment:** Strong. Published in 2026 and uses recent EU working-conditions evidence.
- **Important limitations:** EU-wide evidence, not Turkey-specific and not software-only.

## Rejected Candidates

### rejected_001

- **Candidate:** Random salary aggregation websites for "software engineer salary Turkey"
- **Reason rejected:** Many pages provide salary numbers without sufficiently transparent methodology, survey size, sampling method, or official status. They were not accepted because the project should not present weak salary figures as reliable evidence.

### rejected_002

- **Candidate:** Unverified blog posts about working abroad as a software engineer
- **Reason rejected:** These sources were often anecdotal, SEO-oriented, or lacked institutional authority. International work questions need official employment, qualification, or immigration sources.

### rejected_003

- **Candidate:** Forum and social-media discussions about salaries, remote work, GPA, and internships
- **Reason rejected:** Useful for discovering student concerns, but not acceptable as factual authority for the knowledge base at this stage.

### rejected_004

- **Candidate:** Narrow company career pages for individual software roles
- **Reason rejected:** They may show isolated job requirements, but they do not provide broad evidence about Computer Engineering employment, salaries, or career progression.

### rejected_005

- **Candidate:** İŞKUR labor-market report pages and PDFs found through search snippets
- **Reason rejected:** İŞKUR is a preferred institution, but during this batch no accessible, inspectable official page/PDF was verified with enough visible ICT/software-specific content to accept confidently. Evidence remains insufficient rather than forced.

### rejected_006

- **Candidate:** Older remote-work and work-life balance reports predating 2022
- **Reason rejected:** Remote work patterns changed substantially after the pandemic, so older sources were rejected unless they were uniquely authoritative. More recent Eurofound and ILO evidence was preferred.

## Batch 3 Summary

- **Sources examined:** 18
- **Sources accepted:** 12
- **Sources rejected:** 6
- **Total accepted sources across all batches:** 32

## Turkey-Specific Evidence Added

- TURKSTAT higher-education employment indicators for 2025.
- TURKSTAT national labor-force statistics for 2025.
- TURKSTAT 2024 labor-cost statistics.
- TURKSTAT 2022 structure of earnings statistics.
- Türkiye Investment Office ICT sector profile.
- International Trade Administration Türkiye ICT sector guide.
- TÜBİSAD 2024 ICT sector market data and trends report page.
- ENIC-NARIC Türkiye qualification recognition profile.

## Salary Evidence Added

- Official TURKSTAT labor-cost evidence for 2024, including sector-level gross wage and gross earnings indicators.
- Official TURKSTAT structure-of-earnings evidence for 2022.
- TURKSTAT higher-education employment indicators with monthly average earnings context for graduate fields/programmes.

Important limitation: No accepted source in this batch provides a complete, current, official Computer Engineering-specific salary table for Türkiye. The current salary evidence should be used cautiously as sector or field context.

## International-Career Evidence Added

- Europass guidance for preparing work documents and qualification recognition checks in Europe.
- European Commission EU Blue Card official information for highly qualified non-EU workers.
- ENIC-NARIC Türkiye recognition profile for higher-education qualifications and recognition authorities.

Important limitation: These sources can support general international-career preparation. They must not be used to provide personalized immigration or legal advice.

## Categories Strengthened

- Employment
- Salaries
- Career Opportunities
- Remote Work
- Work-Life Balance
- Graduate Studies
- Skills and Technologies
- Future Technologies
- Entrepreneurship
- Artificial Intelligence
- Cybersecurity

## Categories Still Weak

- Computer Engineering-specific salary data for Türkiye
- Computer Engineering-specific graduate employment by Turkish university/program
- İŞKUR software/ICT occupation demand evidence
- GPA versus personal projects using Computer Engineering-specific evidence
- Graduating without internship experience in Türkiye
- Career progression timelines for junior-to-senior software/computing roles
- Common Misconceptions
- Student Life beyond official university pages

## Questions Still Lacking Strong Evidence

- What exact salary can a Computer Engineering graduate expect in Türkiye?
- How long does it take to become a senior engineer?
- Can a student with low GPA still get a good job?
- Is a personal project portfolio more important than GPA?
- Can a graduate find a job without an internship?
- Which Computer Engineering specialization is best for a specific student?
- Will AI replace computer engineers, specifically in Türkiye?
- How easy is it for Turkish Computer Engineering graduates to work abroad?

## Stop Point

Batch 3 ends here. Batch 4 should not begin until these sources and limitations are reviewed.
