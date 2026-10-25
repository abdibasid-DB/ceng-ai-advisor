| Group | n | Supported | Correct refusal | Incorrect refusal | Unsupported |
|---|---:|---:|---:|---:|---:|
| ai_future | 14 | 11 → 11 | 0 → 0 | 1 → 1 | 2 → 2 |
| mathematics | 12 | 8 → 7 | 0 → 0 | 3 → 4 | 1 → 1 |
| career_employment | 28 | 10 → 12 | 2 → 2 | 11 → 8 | 5 → 6 |
| student_local | 18 | 4 → 7 | 3 → 3 | 6 → 4 | 5 → 4 |
| programming_software | 18 | 11 → 10 | 0 → 0 | 4 → 6 | 3 → 2 |
| multi_turn | 22 | 9 → 8 | 1 → 1 | 5 → 6 | 7 → 7 |
| out_of_scope | 13 | 0 → 0 | 13 → 13 | 0 → 0 | 0 → 0 |
| unsupported | 13 | 0 → 0 | 13 → 13 | 0 → 0 | 0 → 0 |
| paraphrase | 20 | 13 → 11 | 0 → 0 | 3 → 6 | 4 → 3 |
| **All** | 158 | 66 → 66 | 32 → 32 | 33 → 35 | 27 → 25 |

Runtime errors after: 0.
Mean wall time per case: 37.0 s → 37.5 s.

| Case | Group | Before | After |
|---|---|---|---|
| A071 | ai_future | incorrect_refusal_evidence_exists | correct_evidence_supported |
| A072 | ai_future | unsupported_incorrect_or_misleading | correct_evidence_supported |
| A075 | ai_future | correct_evidence_supported | incorrect_refusal_evidence_exists |
| A077 | ai_future | correct_evidence_supported | unsupported_incorrect_or_misleading |
| M028 | mathematics | correct_evidence_supported | incorrect_refusal_evidence_exists |
| P043 | programming_software | correct_evidence_supported | unsupported_incorrect_or_misleading |
| P045 | programming_software | correct_evidence_supported | incorrect_refusal_evidence_exists |
| P049 | programming_software | unsupported_incorrect_or_misleading | incorrect_refusal_evidence_exists |
| P051 | programming_software | unsupported_incorrect_or_misleading | correct_evidence_supported |
| R097 | career_employment | incorrect_refusal_evidence_exists | correct_evidence_supported |
| R100 | career_employment | incorrect_refusal_evidence_exists | correct_evidence_supported |
| R101 | career_employment | correct_evidence_supported | unsupported_incorrect_or_misleading |
| R104 | career_employment | unsupported_incorrect_or_misleading | correct_evidence_supported |
| R113 | career_employment | incorrect_refusal_evidence_exists | correct_evidence_supported |
| R116 | career_employment | incorrect_refusal_evidence_exists | unsupported_incorrect_or_misleading |
| R121 | career_employment | correct_evidence_supported | incorrect_refusal_evidence_exists |
| S124 | student_local | incorrect_refusal_evidence_exists | correct_evidence_supported |
| S132 | student_local | unsupported_incorrect_or_misleading | correct_evidence_supported |
| S137 | student_local | incorrect_refusal_evidence_exists | correct_evidence_supported |
| T179 | multi_turn | incorrect_refusal_evidence_exists | unsupported_incorrect_or_misleading |
| T180 | multi_turn | unsupported_incorrect_or_misleading | correct_evidence_supported |
| T184 | multi_turn | incorrect_refusal_evidence_exists | correct_evidence_supported |
| T185 | multi_turn | correct_evidence_supported | incorrect_refusal_evidence_exists |
| T188 | multi_turn | correct_evidence_supported | incorrect_refusal_evidence_exists |
| T191 | multi_turn | correct_evidence_supported | unsupported_incorrect_or_misleading |
| T198 | multi_turn | unsupported_incorrect_or_misleading | incorrect_refusal_evidence_exists |
| p005 | paraphrase | unsupported_incorrect_or_misleading | incorrect_refusal_evidence_exists |
| p016 | paraphrase | correct_evidence_supported | incorrect_refusal_evidence_exists |
| p019 | paraphrase | correct_evidence_supported | incorrect_refusal_evidence_exists |