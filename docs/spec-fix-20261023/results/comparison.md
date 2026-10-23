| Group | n | Supported | Correct refusal | Incorrect refusal | Unsupported |
|---|---:|---:|---:|---:|---:|
| ai_future | 14 | 10 → 11 | 0 → 0 | 3 → 1 | 1 → 2 |
| mathematics | 12 | 5 → 9 | 0 → 0 | 5 → 3 | 2 → 0 |
| career_employment | 28 | 12 → 14 | 3 → 3 | 9 → 7 | 4 → 4 |
| student_local | 18 | 4 → 6 | 3 → 3 | 7 → 5 | 4 → 4 |
| programming_software | 18 | 11 → 13 | 0 → 0 | 3 → 2 | 4 → 3 |
| multi_turn | 22 | 11 → 7 | 1 → 1 | 3 → 7 | 7 → 7 |
| out_of_scope | 13 | 0 → 0 | 13 → 13 | 0 → 0 | 0 → 0 |
| unsupported | 13 | 0 → 0 | 13 → 13 | 0 → 0 | 0 → 0 |
| paraphrase | 20 | 16 → 15 | 0 → 0 | 3 → 3 | 1 → 2 |
| **All** | 158 | 69 → 75 | 33 → 33 | 33 → 28 | 23 → 22 |

Runtime errors after: 0.

| Case | Group | Before | After |
|---|---|---|---|
| A069 | ai_future | correct_evidence_supported | unsupported_incorrect_or_misleading |
| A070 | ai_future | incorrect_refusal_evidence_exists | correct_evidence_supported |
| A072 | ai_future | correct_evidence_supported | unsupported_incorrect_or_misleading |
| A075 | ai_future | unsupported_incorrect_or_misleading | correct_evidence_supported |
| A076 | ai_future | incorrect_refusal_evidence_exists | correct_evidence_supported |
| M027 | mathematics | incorrect_refusal_evidence_exists | correct_evidence_supported |
| M030 | mathematics | unsupported_incorrect_or_misleading | correct_evidence_supported |
| M035 | mathematics | incorrect_refusal_evidence_exists | correct_evidence_supported |
| M036 | mathematics | unsupported_incorrect_or_misleading | correct_evidence_supported |
| P039 | programming_software | unsupported_incorrect_or_misleading | correct_evidence_supported |
| P040 | programming_software | incorrect_refusal_evidence_exists | correct_evidence_supported |
| P041 | programming_software | incorrect_refusal_evidence_exists | unsupported_incorrect_or_misleading |
| P046 | programming_software | correct_evidence_supported | incorrect_refusal_evidence_exists |
| P048 | programming_software | unsupported_incorrect_or_misleading | correct_evidence_supported |
| R100 | career_employment | incorrect_refusal_evidence_exists | correct_evidence_supported |
| R103 | career_employment | correct_evidence_supported | unsupported_incorrect_or_misleading |
| R104 | career_employment | unsupported_incorrect_or_misleading | correct_evidence_supported |
| R109 | career_employment | incorrect_refusal_evidence_exists | correct_evidence_supported |
| R114 | career_employment | unsupported_incorrect_or_misleading | correct_evidence_supported |
| R115 | career_employment | incorrect_refusal_evidence_exists | correct_evidence_supported |
| R116 | career_employment | correct_evidence_supported | incorrect_refusal_evidence_exists |
| R121 | career_employment | correct_evidence_supported | unsupported_incorrect_or_misleading |
| S124 | student_local | incorrect_refusal_evidence_exists | correct_evidence_supported |
| S127 | student_local | incorrect_refusal_evidence_exists | correct_evidence_supported |
| S132 | student_local | correct_evidence_supported | incorrect_refusal_evidence_exists |
| S135 | student_local | incorrect_refusal_evidence_exists | correct_evidence_supported |
| T179 | multi_turn | correct_evidence_supported | incorrect_refusal_evidence_exists |
| T180 | multi_turn | correct_evidence_supported | unsupported_incorrect_or_misleading |
| T182 | multi_turn | unsupported_incorrect_or_misleading | correct_evidence_supported |
| T184 | multi_turn | incorrect_refusal_evidence_exists | unsupported_incorrect_or_misleading |
| T186 | multi_turn | correct_evidence_supported | unsupported_incorrect_or_misleading |
| T187 | multi_turn | unsupported_incorrect_or_misleading | incorrect_refusal_evidence_exists |
| T188 | multi_turn | unsupported_incorrect_or_misleading | incorrect_refusal_evidence_exists |
| T189 | multi_turn | unsupported_incorrect_or_misleading | incorrect_refusal_evidence_exists |
| T192 | multi_turn | correct_evidence_supported | incorrect_refusal_evidence_exists |
| T194 | multi_turn | incorrect_refusal_evidence_exists | unsupported_incorrect_or_misleading |
| T197 | multi_turn | correct_evidence_supported | incorrect_refusal_evidence_exists |
| p007 | paraphrase | incorrect_refusal_evidence_exists | correct_evidence_supported |
| p009 | paraphrase | correct_evidence_supported | unsupported_incorrect_or_misleading |
| p020 | paraphrase | correct_evidence_supported | incorrect_refusal_evidence_exists |