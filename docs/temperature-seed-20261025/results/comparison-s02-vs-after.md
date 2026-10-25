| Group | n | Supported | Correct refusal | Incorrect refusal | Unsupported |
|---|---:|---:|---:|---:|---:|
| ai_future | 14 | 11 → 11 | 0 → 0 | 1 → 1 | 2 → 2 |
| mathematics | 12 | 9 → 7 | 0 → 0 | 3 → 4 | 0 → 1 |
| career_employment | 28 | 14 → 12 | 3 → 2 | 7 → 8 | 4 → 6 |
| student_local | 18 | 6 → 7 | 3 → 3 | 5 → 4 | 4 → 4 |
| programming_software | 18 | 13 → 10 | 0 → 0 | 2 → 6 | 3 → 2 |
| multi_turn | 22 | 7 → 8 | 1 → 1 | 7 → 6 | 7 → 7 |
| out_of_scope | 13 | 0 → 0 | 13 → 13 | 0 → 0 | 0 → 0 |
| unsupported | 13 | 0 → 0 | 13 → 13 | 0 → 0 | 0 → 0 |
| paraphrase | 20 | 15 → 11 | 0 → 0 | 3 → 6 | 2 → 3 |
| **All** | 158 | 75 → 66 | 33 → 32 | 28 → 35 | 22 → 25 |

Runtime errors after: 0.
Mean wall time per case: 30.8 s → 37.5 s.

| Case | Group | Before | After |
|---|---|---|---|
| A072 | ai_future | unsupported_incorrect_or_misleading | correct_evidence_supported |
| A075 | ai_future | correct_evidence_supported | incorrect_refusal_evidence_exists |
| A077 | ai_future | correct_evidence_supported | unsupported_incorrect_or_misleading |
| A081 | ai_future | incorrect_refusal_evidence_exists | correct_evidence_supported |
| M032 | mathematics | correct_evidence_supported | incorrect_refusal_evidence_exists |
| M035 | mathematics | correct_evidence_supported | unsupported_incorrect_or_misleading |
| P039 | programming_software | correct_evidence_supported | unsupported_incorrect_or_misleading |
| P040 | programming_software | correct_evidence_supported | incorrect_refusal_evidence_exists |
| P041 | programming_software | unsupported_incorrect_or_misleading | incorrect_refusal_evidence_exists |
| P045 | programming_software | correct_evidence_supported | incorrect_refusal_evidence_exists |
| P049 | programming_software | correct_evidence_supported | incorrect_refusal_evidence_exists |
| P053 | programming_software | unsupported_incorrect_or_misleading | correct_evidence_supported |
| R096 | career_employment | correct_insufficient_information | unsupported_incorrect_or_misleading |
| R101 | career_employment | correct_evidence_supported | unsupported_incorrect_or_misleading |
| R109 | career_employment | correct_evidence_supported | incorrect_refusal_evidence_exists |
| R113 | career_employment | incorrect_refusal_evidence_exists | correct_evidence_supported |
| R116 | career_employment | incorrect_refusal_evidence_exists | unsupported_incorrect_or_misleading |
| R117 | career_employment | correct_evidence_supported | incorrect_refusal_evidence_exists |
| R121 | career_employment | unsupported_incorrect_or_misleading | incorrect_refusal_evidence_exists |
| S127 | student_local | correct_evidence_supported | incorrect_refusal_evidence_exists |
| S128 | student_local | incorrect_refusal_evidence_exists | correct_evidence_supported |
| S132 | student_local | incorrect_refusal_evidence_exists | correct_evidence_supported |
| S135 | student_local | correct_evidence_supported | incorrect_refusal_evidence_exists |
| S140 | student_local | incorrect_refusal_evidence_exists | correct_evidence_supported |
| T179 | multi_turn | incorrect_refusal_evidence_exists | unsupported_incorrect_or_misleading |
| T180 | multi_turn | unsupported_incorrect_or_misleading | correct_evidence_supported |
| T183 | multi_turn | correct_evidence_supported | unsupported_incorrect_or_misleading |
| T184 | multi_turn | unsupported_incorrect_or_misleading | correct_evidence_supported |
| T185 | multi_turn | correct_evidence_supported | incorrect_refusal_evidence_exists |
| T186 | multi_turn | unsupported_incorrect_or_misleading | correct_evidence_supported |
| T187 | multi_turn | incorrect_refusal_evidence_exists | unsupported_incorrect_or_misleading |
| T189 | multi_turn | incorrect_refusal_evidence_exists | correct_evidence_supported |
| T194 | multi_turn | unsupported_incorrect_or_misleading | incorrect_refusal_evidence_exists |
| T197 | multi_turn | incorrect_refusal_evidence_exists | unsupported_incorrect_or_misleading |
| T198 | multi_turn | correct_evidence_supported | incorrect_refusal_evidence_exists |
| p007 | paraphrase | correct_evidence_supported | incorrect_refusal_evidence_exists |
| p016 | paraphrase | correct_evidence_supported | incorrect_refusal_evidence_exists |
| p018 | paraphrase | correct_evidence_supported | unsupported_incorrect_or_misleading |
| p019 | paraphrase | correct_evidence_supported | incorrect_refusal_evidence_exists |