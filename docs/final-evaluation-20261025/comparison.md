# Final evaluation (2026-10-25) vs 2026-10-18 and 2026-10-23

The 2026-10-18 run is incomplete (193 of 200 cases). The first two tables label all three runs again with the current official classifier, because it calls the pipeline's topic check, which the spec fix (208e21d) changed; the third table uses the labels recorded at run time.

Mean s/answer is `elapsed_wall_seconds` per case; for multi-turn cases it includes the setup turn.

### All cases (current classifier)

Each cell: Oct 18 / Oct 23 / Oct 25.

| Category | n | Supported | Correct refusal | Incorrect refusal | Unsupported | Error | Mean s/answer |
|---|---:|---:|---:|---:|---:|---:|---:|
| ai_future | 14 / 14 / 14 | 7 / 10 / 11 | 0 / 0 / 0 | 6 / 3 / 1 | 1 / 1 / 2 | 0 / 0 / 0 | 41.1 / 34.3 / 39.6 |
| career_employment | 28 / 28 / 28 | 10 / 12 / 10 | 2 / 3 / 2 | 12 / 9 / 12 | 4 / 4 / 4 | 0 / 0 / 0 | 27.1 / 32.4 / 43.2 |
| complex | 12 / 12 / 12 | 6 / 7 / 4 | 1 / 0 / 0 | 4 / 4 / 5 | 1 / 1 / 3 | 0 / 0 / 0 | 26.8 / 21.7 / 29.7 |
| curriculum | 14 / 14 / 14 | 8 / 9 / 11 | 0 / 0 / 0 | 4 / 3 / 3 | 2 / 2 / 0 | 0 / 0 / 0 | 26.9 / 23.8 / 34.0 |
| cybersecurity | 12 / 12 / 12 | 10 / 10 / 10 | 0 / 0 / 0 | 1 / 2 / 2 | 1 / 0 / 0 | 0 / 0 / 0 | 28.4 / 30.7 / 39.5 |
| fundamentals | 12 / 12 / 12 | 9 / 10 / 8 | 0 / 0 / 0 | 1 / 0 / 1 | 2 / 2 / 3 | 0 / 0 / 0 | 25.0 / 32.8 / 37.8 |
| hardware_networks | 12 / 12 / 12 | 8 / 7 / 9 | 0 / 0 / 0 | 4 / 4 / 3 | 0 / 1 / 0 | 0 / 0 / 0 | 25.7 / 23.6 / 32.8 |
| mathematics | 12 / 12 / 12 | 8 / 5 / 8 | 0 / 0 / 0 | 4 / 5 / 3 | 0 / 2 / 1 | 0 / 0 / 0 | 33.2 / 35.2 / 32.3 |
| multi_turn | 15 / 22 / 22 | 7 / 11 / 8 | 1 / 1 / 1 | 4 / 3 / 6 | 3 / 7 / 7 | 0 / 0 / 0 | 64.2 / 71.5 / 76.3 |
| out_of_scope | 13 / 13 / 13 | 0 / 0 / 0 | 13 / 13 / 13 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0.0 / 0.0 / 0.0 |
| programming_software | 18 / 18 / 18 | 13 / 11 / 11 | 0 / 0 / 0 | 3 / 3 / 5 | 2 / 4 / 2 | 0 / 0 / 0 | 24.3 / 24.0 / 34.7 |
| student_local | 18 / 18 / 18 | 6 / 4 / 5 | 4 / 3 / 3 | 7 / 7 / 5 | 1 / 4 / 5 | 0 / 0 / 0 | 20.5 / 27.1 / 36.7 |
| unsupported | 13 / 13 / 13 | 0 / 0 / 0 | 13 / 13 / 13 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0.0 / 0.2 / 0.2 |
| **All** | 193 / 200 / 200 | 92 / 96 / 95 | 34 / 33 / 32 | 50 / 43 / 46 | 17 / 28 / 27 | 0 / 0 / 0 | 26.7 / 29.7 / 36.3 |

### Same case IDs as 2026-10-18 (current classifier)

Each cell: Oct 18 / Oct 23 / Oct 25.

| Category | n | Supported | Correct refusal | Incorrect refusal | Unsupported | Error | Mean s/answer |
|---|---:|---:|---:|---:|---:|---:|---:|
| ai_future | 14 / 14 / 14 | 7 / 10 / 11 | 0 / 0 / 0 | 6 / 3 / 1 | 1 / 1 / 2 | 0 / 0 / 0 | 41.1 / 34.3 / 39.6 |
| career_employment | 28 / 28 / 28 | 10 / 12 / 10 | 2 / 3 / 2 | 12 / 9 / 12 | 4 / 4 / 4 | 0 / 0 / 0 | 27.1 / 32.4 / 43.2 |
| complex | 12 / 12 / 12 | 6 / 7 / 4 | 1 / 0 / 0 | 4 / 4 / 5 | 1 / 1 / 3 | 0 / 0 / 0 | 26.8 / 21.7 / 29.7 |
| curriculum | 14 / 14 / 14 | 8 / 9 / 11 | 0 / 0 / 0 | 4 / 3 / 3 | 2 / 2 / 0 | 0 / 0 / 0 | 26.9 / 23.8 / 34.0 |
| cybersecurity | 12 / 12 / 12 | 10 / 10 / 10 | 0 / 0 / 0 | 1 / 2 / 2 | 1 / 0 / 0 | 0 / 0 / 0 | 28.4 / 30.7 / 39.5 |
| fundamentals | 12 / 12 / 12 | 9 / 10 / 8 | 0 / 0 / 0 | 1 / 0 / 1 | 2 / 2 / 3 | 0 / 0 / 0 | 25.0 / 32.8 / 37.8 |
| hardware_networks | 12 / 12 / 12 | 8 / 7 / 9 | 0 / 0 / 0 | 4 / 4 / 3 | 0 / 1 / 0 | 0 / 0 / 0 | 25.7 / 23.6 / 32.8 |
| mathematics | 12 / 12 / 12 | 8 / 5 / 8 | 0 / 0 / 0 | 4 / 5 / 3 | 0 / 2 / 1 | 0 / 0 / 0 | 33.2 / 35.2 / 32.3 |
| multi_turn | 15 / 15 / 15 | 7 / 7 / 7 | 1 / 1 / 1 | 4 / 1 / 3 | 3 / 6 / 4 | 0 / 0 / 0 | 64.2 / 70.8 / 77.5 |
| out_of_scope | 13 / 13 / 13 | 0 / 0 / 0 | 13 / 13 / 13 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0.0 / 0.0 / 0.0 |
| programming_software | 18 / 18 / 18 | 13 / 11 / 11 | 0 / 0 / 0 | 3 / 3 / 5 | 2 / 4 / 2 | 0 / 0 / 0 | 24.3 / 24.0 / 34.7 |
| student_local | 18 / 18 / 18 | 6 / 4 / 5 | 4 / 3 / 3 | 7 / 7 / 5 | 1 / 4 / 5 | 0 / 0 / 0 | 20.5 / 27.1 / 36.7 |
| unsupported | 13 / 13 / 13 | 0 / 0 / 0 | 13 / 13 / 13 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0.0 / 0.2 / 0.2 |
| **All** | 193 / 193 / 193 | 92 / 92 / 94 | 34 / 33 / 32 | 50 / 41 / 43 | 17 / 27 / 24 | 0 / 0 / 0 | 26.7 / 28.2 / 35.0 |

### All cases (labels recorded at run time)

Each cell: Oct 18 / Oct 23 / Oct 25.

| Category | n | Supported | Correct refusal | Incorrect refusal | Unsupported | Error | Mean s/answer |
|---|---:|---:|---:|---:|---:|---:|---:|
| ai_future | 14 / 14 / 14 | 7 / 10 / 11 | 0 / 0 / 0 | 6 / 3 / 1 | 1 / 1 / 2 | 0 / 0 / 0 | 41.1 / 34.3 / 39.6 |
| career_employment | 28 / 28 / 28 | 10 / 12 / 10 | 2 / 3 / 2 | 12 / 9 / 12 | 4 / 4 / 4 | 0 / 0 / 0 | 27.1 / 32.4 / 43.2 |
| complex | 12 / 12 / 12 | 6 / 7 / 4 | 1 / 0 / 0 | 4 / 4 / 5 | 1 / 1 / 3 | 0 / 0 / 0 | 26.8 / 21.7 / 29.7 |
| curriculum | 14 / 14 / 14 | 8 / 9 / 11 | 0 / 0 / 0 | 4 / 3 / 3 | 2 / 2 / 0 | 0 / 0 / 0 | 26.9 / 23.8 / 34.0 |
| cybersecurity | 12 / 12 / 12 | 9 / 9 / 10 | 0 / 0 / 0 | 1 / 2 / 2 | 2 / 1 / 0 | 0 / 0 / 0 | 28.4 / 30.7 / 39.5 |
| fundamentals | 12 / 12 / 12 | 9 / 10 / 8 | 0 / 0 / 0 | 1 / 0 / 1 | 2 / 2 / 3 | 0 / 0 / 0 | 25.0 / 32.8 / 37.8 |
| hardware_networks | 12 / 12 / 12 | 8 / 7 / 9 | 0 / 0 / 0 | 4 / 4 / 3 | 0 / 1 / 0 | 0 / 0 / 0 | 25.7 / 23.6 / 32.8 |
| mathematics | 12 / 12 / 12 | 8 / 5 / 8 | 0 / 0 / 0 | 4 / 5 / 3 | 0 / 2 / 1 | 0 / 0 / 0 | 33.2 / 35.2 / 32.3 |
| multi_turn | 15 / 22 / 22 | 6 / 10 / 8 | 1 / 1 / 1 | 4 / 3 / 6 | 4 / 8 / 7 | 0 / 0 / 0 | 64.2 / 71.5 / 76.3 |
| out_of_scope | 13 / 13 / 13 | 0 / 0 / 0 | 13 / 13 / 13 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0.0 / 0.0 / 0.0 |
| programming_software | 18 / 18 / 18 | 13 / 11 / 11 | 0 / 0 / 0 | 3 / 3 / 5 | 2 / 4 / 2 | 0 / 0 / 0 | 24.3 / 24.0 / 34.7 |
| student_local | 18 / 18 / 18 | 6 / 4 / 5 | 4 / 3 / 3 | 7 / 7 / 5 | 1 / 4 / 5 | 0 / 0 / 0 | 20.5 / 27.1 / 36.7 |
| unsupported | 13 / 13 / 13 | 0 / 0 / 0 | 13 / 13 / 13 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0.0 / 0.2 / 0.2 |
| **All** | 193 / 200 / 200 | 90 / 94 / 95 | 34 / 33 / 32 | 50 / 43 / 46 | 19 / 30 / 27 | 0 / 0 / 0 | 26.7 / 29.7 / 36.3 |

### 60 ceng-questions (scripts/evaluate_rag_quality.py)

| | Oct 23 | Oct 25 |
|---|---:|---:|
| answered | 43 | 37 |
| insufficient_information | 17 | 23 |
| Appropriate refusal / insufficient information | 8 | 12 |
| Correct / well-supported | 42 | 34 |
| Partially correct / partially supported | 9 | 11 |
| Unsupported or incorrect | 1 | 3 |
| Highly relevant | 47 | 47 |
| Irrelevant | 5 | 5 |
| Relevant | 8 | 8 |
| answered with valid citations | 43 | 37 |
| mean s/answer | 27.0 | 35.3 |

### Specification questions

| Case | Oct 23 | Oct 25 |
|---|---|---|
| SPEC1 | insufficient_information | insufficient_information |
| SPEC2 | insufficient_information | answered |
| SPEC3 | answered | answered |
| SPEC4 | insufficient_information | answered |

### Label changes Oct 23 → Oct 25 (current classifier): 53

| Case | Group | Oct 23 | Oct 25 |
|---|---|---|---|
| A069 | ai_future | correct_evidence_supported | unsupported_incorrect_or_misleading |
| A070 | ai_future | incorrect_refusal_evidence_exists | correct_evidence_supported |
| A071 | ai_future | correct_evidence_supported | incorrect_refusal_evidence_exists |
| A072 | ai_future | correct_evidence_supported | unsupported_incorrect_or_misleading |
| A075 | ai_future | unsupported_incorrect_or_misleading | correct_evidence_supported |
| A076 | ai_future | incorrect_refusal_evidence_exists | correct_evidence_supported |
| A081 | ai_future | incorrect_refusal_evidence_exists | correct_evidence_supported |
| C021 | curriculum | unsupported_incorrect_or_misleading | correct_evidence_supported |
| C023 | curriculum | unsupported_incorrect_or_misleading | correct_evidence_supported |
| F008 | fundamentals | correct_evidence_supported | unsupported_incorrect_or_misleading |
| F012 | fundamentals | correct_evidence_supported | incorrect_refusal_evidence_exists |
| H061 | hardware_networks | correct_evidence_supported | incorrect_refusal_evidence_exists |
| H062 | hardware_networks | incorrect_refusal_evidence_exists | correct_evidence_supported |
| H064 | hardware_networks | incorrect_refusal_evidence_exists | correct_evidence_supported |
| H067 | hardware_networks | unsupported_incorrect_or_misleading | correct_evidence_supported |
| M027 | mathematics | incorrect_refusal_evidence_exists | correct_evidence_supported |
| M028 | mathematics | incorrect_refusal_evidence_exists | correct_evidence_supported |
| M030 | mathematics | unsupported_incorrect_or_misleading | correct_evidence_supported |
| M032 | mathematics | correct_evidence_supported | incorrect_refusal_evidence_exists |
| M035 | mathematics | incorrect_refusal_evidence_exists | unsupported_incorrect_or_misleading |
| M036 | mathematics | unsupported_incorrect_or_misleading | correct_evidence_supported |
| P043 | programming_software | unsupported_incorrect_or_misleading | correct_evidence_supported |
| P046 | programming_software | correct_evidence_supported | incorrect_refusal_evidence_exists |
| P048 | programming_software | unsupported_incorrect_or_misleading | correct_evidence_supported |
| P049 | programming_software | correct_evidence_supported | incorrect_refusal_evidence_exists |
| P051 | programming_software | correct_evidence_supported | unsupported_incorrect_or_misleading |
| P053 | programming_software | unsupported_incorrect_or_misleading | correct_evidence_supported |
| R096 | career_employment | correct_insufficient_information | incorrect_refusal_evidence_exists |
| R097 | career_employment | correct_evidence_supported | incorrect_refusal_evidence_exists |
| R103 | career_employment | correct_evidence_supported | unsupported_incorrect_or_misleading |
| R107 | career_employment | incorrect_refusal_evidence_exists | correct_evidence_supported |
| R114 | career_employment | unsupported_incorrect_or_misleading | correct_evidence_supported |
| R116 | career_employment | correct_evidence_supported | incorrect_refusal_evidence_exists |
| R117 | career_employment | correct_evidence_supported | incorrect_refusal_evidence_exists |
| S127 | student_local | incorrect_refusal_evidence_exists | correct_evidence_supported |
| S128 | student_local | incorrect_refusal_evidence_exists | correct_evidence_supported |
| S132 | student_local | correct_evidence_supported | unsupported_incorrect_or_misleading |
| T179 | multi_turn | correct_evidence_supported | incorrect_refusal_evidence_exists |
| T180 | multi_turn | correct_evidence_supported | unsupported_incorrect_or_misleading |
| T182 | multi_turn | unsupported_incorrect_or_misleading | correct_evidence_supported |
| T183 | multi_turn | correct_evidence_supported | unsupported_incorrect_or_misleading |
| T188 | multi_turn | unsupported_incorrect_or_misleading | correct_evidence_supported |
| T189 | multi_turn | unsupported_incorrect_or_misleading | correct_evidence_supported |
| T191 | multi_turn | unsupported_incorrect_or_misleading | correct_evidence_supported |
| T192 | multi_turn | correct_evidence_supported | incorrect_refusal_evidence_exists |
| T197 | multi_turn | correct_evidence_supported | unsupported_incorrect_or_misleading |
| T198 | multi_turn | correct_evidence_supported | unsupported_incorrect_or_misleading |
| T200 | multi_turn | correct_evidence_supported | incorrect_refusal_evidence_exists |
| X141 | complex | correct_evidence_supported | incorrect_refusal_evidence_exists |
| X144 | complex | correct_evidence_supported | unsupported_incorrect_or_misleading |
| X150 | complex | correct_evidence_supported | unsupported_incorrect_or_misleading |
| Y084 | cybersecurity | incorrect_refusal_evidence_exists | correct_evidence_supported |
| Y092 | cybersecurity | correct_evidence_supported | incorrect_refusal_evidence_exists |
