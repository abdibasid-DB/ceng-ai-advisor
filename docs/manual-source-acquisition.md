# Manual Source Acquisition

## Purpose

This document lists the approved sources that still cannot be legitimately acquired automatically after Stage 8B manual source resolution.

Do not use replacement URLs, third-party mirrors, cached copies from unknown sites, CAPTCHA bypasses, authentication bypasses, or copied text from unrelated pages. Save only the exact approved source content, or an official download/print version clearly provided by the same approved source organization.

## Sources Resolved During Stage 8B

The following previously manual-required sources were resolved by saving official same-organization PDF downloads:

| Source ID | Local file |
|---|---|
| src_016 | `knowledge_base/raw/pdf/src_016.pdf` |
| src_017 | `knowledge_base/raw/pdf/src_017.pdf` |
| src_031 | `knowledge_base/raw/pdf/src_031.pdf` |
| src_045 | `knowledge_base/raw/pdf/src_045.pdf` |
| src_046 | `knowledge_base/raw/pdf/src_046.pdf` |

These files passed basic PDF header and size checks and are recorded in `knowledge_base/sources.json`.

## Remaining Manual Acquisition Targets

### src_009

- **Title:** Curricula Recommendations
- **URL:** https://www.acm.org/education/curricula-recommendations
- **Reason automatic acquisition failed:** HTTP 403 Forbidden
- **Expected file type:** HTML
- **Destination path:** `knowledge_base/raw/html/src_009.html`

Manual steps:

1. Open the exact URL in your normal browser.
2. If the page loads publicly, press `Ctrl+S`.
3. Choose `Webpage, HTML Only` if available.
4. Save the file as `src_009.html`.
5. Save it into `knowledge_base\raw\html\`.
6. Confirm it contains ACM Curricula Recommendations content, not an access-denied or login page.

### src_010

- **Title:** Software Developers, Quality Assurance Analysts, and Testers
- **URL:** https://www.bls.gov/ooh/computer-and-information-technology/software-developers.htm
- **Reason automatic acquisition failed:** HTTP 403 Forbidden
- **Expected file type:** HTML
- **Destination path:** `knowledge_base/raw/html/src_010.html`

Manual steps:

1. Open the exact BLS URL in your normal browser.
2. If the regular page opens, use the official printer-friendly option if visible, or press `Ctrl+S`.
3. Choose `Webpage, HTML Only`.
4. Save the file as `src_010.html`.
5. Save it into `knowledge_base\raw\html\`.
6. Confirm the saved file contains the BLS occupational profile, not a BLS "Access Denied" page.

### src_011

- **Title:** Computer Hardware Engineers
- **URL:** https://www.bls.gov/ooh/architecture-and-engineering/computer-hardware-engineers.htm
- **Reason automatic acquisition failed:** HTTP 403 Forbidden
- **Expected file type:** HTML
- **Destination path:** `knowledge_base/raw/html/src_011.html`

Manual steps:

1. Open the exact BLS URL in your normal browser.
2. If available, use the official BLS printer-friendly option; otherwise press `Ctrl+S`.
3. Choose `Webpage, HTML Only`.
4. Save the file as `src_011.html`.
5. Save it into `knowledge_base\raw\html\`.
6. Confirm it contains the BLS Computer Hardware Engineers profile.

### src_012

- **Title:** Information Security Analysts
- **URL:** https://www.bls.gov/ooh/computer-and-information-technology/information-security-analysts.htm
- **Reason automatic acquisition failed:** HTTP 403 Forbidden
- **Expected file type:** HTML
- **Destination path:** `knowledge_base/raw/html/src_012.html`

Manual steps:

1. Open the exact BLS URL in your normal browser.
2. If available, use the official BLS printer-friendly option; otherwise press `Ctrl+S`.
3. Choose `Webpage, HTML Only`.
4. Save the file as `src_012.html`.
5. Save it into `knowledge_base\raw\html\`.
6. Confirm it contains the BLS Information Security Analysts profile.

### src_013

- **Title:** Computer and Information Research Scientists
- **URL:** https://www.bls.gov/ooh/computer-and-information-technology/computer-and-information-research-scientists.htm
- **Reason automatic acquisition failed:** HTTP 403 Forbidden
- **Expected file type:** HTML
- **Destination path:** `knowledge_base/raw/html/src_013.html`

Manual steps:

1. Open the exact BLS URL in your normal browser.
2. If available, use the official BLS printer-friendly option; otherwise press `Ctrl+S`.
3. Choose `Webpage, HTML Only`.
4. Save the file as `src_013.html`.
5. Save it into `knowledge_base\raw\html\`.
6. Confirm it contains the BLS Computer and Information Research Scientists profile.

### src_032

- **Title:** Working anytime, anywhere: The quality of working time in the EU
- **URL:** https://www.eurofound.europa.eu/default/publications/all/working-anytime-anywhere-the-quality-of-working-time-in-the-eu
- **Reason automatic acquisition failed:** HTTP 429 Too Many Requests
- **Expected file type:** HTML, or official Eurofound PDF if provided on the page
- **Destination path:** `knowledge_base/raw/html/src_032.html` or `knowledge_base/raw/pdf/src_032.pdf`

Manual steps:

1. Open the exact Eurofound URL in your normal browser.
2. If the page provides an official `Download PDF` button, download the official PDF.
3. Save the PDF as `src_032.pdf` into `knowledge_base\raw\pdf\`.
4. If no PDF is available, press `Ctrl+S`, choose `Webpage, HTML Only`, and save as `src_032.html`.
5. Confirm the saved content is the Eurofound report page or official PDF, not a rate-limit page.

### src_042

- **Title:** Curricular Guidance
- **URL:** https://ccecc.acm.org/guidance
- **Reason automatic acquisition failed:** HTTP 200 returned, but integrity check detected possible error/login/bot-block content
- **Expected file type:** HTML
- **Destination path:** `knowledge_base/raw/html/src_042.html`

Manual steps:

1. Open the exact ACM CCECC URL in your normal browser.
2. If the page loads publicly, press `Ctrl+S`.
3. Choose `Webpage, HTML Only`.
4. Save the file as `src_042.html`.
5. Save it into `knowledge_base\raw\html\`.
6. Confirm it contains ACM CCECC curricular guidance, not an error or login page.

### src_043

- **Title:** Subdisciplines
- **URL:** https://ece.illinois.edu/academics/ugrad/subdisciplines
- **Reason automatic acquisition failed:** HTTP 200 returned, but integrity check detected possible error/login/bot-block content
- **Expected file type:** HTML
- **Destination path:** `knowledge_base/raw/html/src_043.html`

Manual steps:

1. Open the exact UIUC ECE URL in your normal browser.
2. If the page loads publicly, press `Ctrl+S`.
3. Choose `Webpage, HTML Only`.
4. Save the file as `src_043.html`.
5. Save it into `knowledge_base\raw\html\`.
6. Confirm it contains the UIUC ECE subdisciplines content.

### src_047

- **Title:** Education GPS - Türkiye - Overview of the education system (EAG 2025)
- **URL:** https://gpseducation.oecd.org/CountryProfile?primaryCountry=TUR&topic=EO&treshold=5
- **Reason automatic acquisition failed:** HTTP 403 Forbidden
- **Expected file type:** HTML or official OECD export if available on the page
- **Destination path:** `knowledge_base/raw/html/src_047.html`

Manual steps:

1. Open the exact OECD Education GPS URL in your normal browser.
2. If the page loads publicly, use any official export/download option on that page if it preserves the same Türkiye profile content.
3. If no export is available, press `Ctrl+S`.
4. Choose `Webpage, HTML Only`.
5. Save the file as `src_047.html`.
6. Save it into `knowledge_base\raw\html\`.
7. Confirm it contains the OECD Education GPS Türkiye profile content.

### src_055

- **Title:** Investigating Academic Confidence, Workload Stress, and Performance in a BlendFlex Computer Science Course
- **URL:** https://doi.org/10.1145/3649217.3653606
- **Reason automatic acquisition failed:** HTTP 403 Forbidden
- **Expected file type:** Official ACM landing page HTML or legally available official PDF
- **Destination path:** `knowledge_base/raw/html/src_055.html` or `knowledge_base/raw/pdf/src_055.pdf`

Manual steps:

1. Open the DOI URL in your normal browser.
2. Let the DOI redirect to the official ACM page.
3. If your institution/browser gives legal access to an official PDF, download it.
4. Save the PDF as `src_055.pdf` into `knowledge_base\raw\pdf\`.
5. If no PDF access is available, save only the official ACM landing page as `src_055.html` into `knowledge_base\raw\html\`.
6. Do not use unauthorized mirrors or uploaded copies.

### src_056

- **Title:** How Beginning Programmers and Code LLMs (Mis)read Each Other
- **URL:** https://doi.org/10.1145/3613904.3642706
- **Reason automatic acquisition failed:** HTTP 403 Forbidden
- **Expected file type:** Official ACM landing page HTML or legally available official PDF
- **Destination path:** `knowledge_base/raw/html/src_056.html` or `knowledge_base/raw/pdf/src_056.pdf`

Manual steps:

1. Open the DOI URL in your normal browser.
2. Let the DOI redirect to the official ACM page.
3. If your institution/browser gives legal access to an official PDF, download it.
4. Save the PDF as `src_056.pdf` into `knowledge_base\raw\pdf\`.
5. If no PDF access is available, save only the official ACM landing page as `src_056.html` into `knowledge_base\raw\html\`.
6. Do not use unauthorized mirrors or uploaded copies.

## Validation After Manual Downloads

After saving any manual files, run:

```powershell
python scripts\acquire_sources.py --timeout 25 --retries 1
```

The script will mark valid existing files as `skipped_existing` and update `raw_file_path` in `knowledge_base/sources.json`.
