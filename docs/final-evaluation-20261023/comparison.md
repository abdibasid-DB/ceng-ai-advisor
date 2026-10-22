# Final evaluation vs 2026-10-18

The 2026-10-18 run is incomplete (193 of 200 cases); the second table restricts the new run to the same case IDs.

Mean s/answer is `elapsed_wall_seconds` per case in both runs; for multi-turn cases it includes the setup turn, so it is higher than the per-answer latency in full200-report.md.

### All cases

| Category | n (Oct 18 / now) | Supported | Correct refusal | Incorrect refusal | Unsupported | Mean s/answer |
|---|---:|---:|---:|---:|---:|---:|
| ai_future | 14 / 14 | 7 → 10 | 0 → 0 | 6 → 3 | 1 → 1 | 41.1 → 34.3 |
| career_employment | 28 / 28 | 10 → 12 | 2 → 3 | 12 → 9 | 4 → 4 | 27.1 → 32.4 |
| complex | 12 / 12 | 6 → 7 | 1 → 0 | 4 → 4 | 1 → 1 | 26.8 → 21.7 |
| curriculum | 14 / 14 | 8 → 9 | 0 → 0 | 4 → 3 | 2 → 2 | 26.9 → 23.8 |
| cybersecurity | 12 / 12 | 9 → 9 | 0 → 0 | 1 → 2 | 2 → 1 | 28.4 → 30.7 |
| fundamentals | 12 / 12 | 9 → 10 | 0 → 0 | 1 → 0 | 2 → 2 | 25.0 → 32.8 |
| hardware_networks | 12 / 12 | 8 → 7 | 0 → 0 | 4 → 4 | 0 → 1 | 25.7 → 23.6 |
| mathematics | 12 / 12 | 8 → 5 | 0 → 0 | 4 → 5 | 0 → 2 | 33.2 → 35.2 |
| multi_turn | 15 / 22 | 6 → 10 | 1 → 1 | 4 → 3 | 4 → 8 | 64.2 → 71.5 |
| out_of_scope | 13 / 13 | 0 → 0 | 13 → 13 | 0 → 0 | 0 → 0 | 0.0 → 0.0 |
| programming_software | 18 / 18 | 13 → 11 | 0 → 0 | 3 → 3 | 2 → 4 | 24.3 → 24.0 |
| student_local | 18 / 18 | 6 → 4 | 4 → 3 | 7 → 7 | 1 → 4 | 20.5 → 27.1 |
| unsupported | 13 / 13 | 0 → 0 | 13 → 13 | 0 → 0 | 0 → 0 | 0.0 → 0.2 |
| **All** | 193 / 200 | 90 → 94 | 34 → 33 | 50 → 43 | 19 → 30 | 26.7 → 29.7 |

### Same case IDs as 2026-10-18

| Category | n (Oct 18 / now) | Supported | Correct refusal | Incorrect refusal | Unsupported | Mean s/answer |
|---|---:|---:|---:|---:|---:|---:|
| ai_future | 14 / 14 | 7 → 10 | 0 → 0 | 6 → 3 | 1 → 1 | 41.1 → 34.3 |
| career_employment | 28 / 28 | 10 → 12 | 2 → 3 | 12 → 9 | 4 → 4 | 27.1 → 32.4 |
| complex | 12 / 12 | 6 → 7 | 1 → 0 | 4 → 4 | 1 → 1 | 26.8 → 21.7 |
| curriculum | 14 / 14 | 8 → 9 | 0 → 0 | 4 → 3 | 2 → 2 | 26.9 → 23.8 |
| cybersecurity | 12 / 12 | 9 → 9 | 0 → 0 | 1 → 2 | 2 → 1 | 28.4 → 30.7 |
| fundamentals | 12 / 12 | 9 → 10 | 0 → 0 | 1 → 0 | 2 → 2 | 25.0 → 32.8 |
| hardware_networks | 12 / 12 | 8 → 7 | 0 → 0 | 4 → 4 | 0 → 1 | 25.7 → 23.6 |
| mathematics | 12 / 12 | 8 → 5 | 0 → 0 | 4 → 5 | 0 → 2 | 33.2 → 35.2 |
| multi_turn | 15 / 15 | 6 → 6 | 1 → 1 | 4 → 1 | 4 → 7 | 64.2 → 70.8 |
| out_of_scope | 13 / 13 | 0 → 0 | 13 → 13 | 0 → 0 | 0 → 0 | 0.0 → 0.0 |
| programming_software | 18 / 18 | 13 → 11 | 0 → 0 | 3 → 3 | 2 → 4 | 24.3 → 24.0 |
| student_local | 18 / 18 | 6 → 4 | 4 → 3 | 7 → 7 | 1 → 4 | 20.5 → 27.1 |
| unsupported | 13 / 13 | 0 → 0 | 13 → 13 | 0 → 0 | 0 → 0 | 0.0 → 0.2 |
| **All** | 193 / 193 | 90 → 90 | 34 → 33 | 50 → 41 | 19 → 29 | 26.7 → 28.2 |
