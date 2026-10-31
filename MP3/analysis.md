# MP3 experiment summary

## Task 1 - Code translation

- Vanilla success rate: 45.0% (9/20)
- Crafted success rate: 70.0% (14/20)
- Absolute improvement: +25.0 percentage points
- Rubric check: **MEETS EXPECTATION - within the expected 20-50 point range**
- Vanilla outcomes: compilation_error: 7, pass: 9, test_failure: 4
- Crafted outcomes: compilation_error: 2, pass: 14, test_failure: 4

| Task ID | Vanilla | Crafted | Vanilla category | Crafted category |
|---|---:|---:|---|---|
| HumanEval/8 | False (test failure) | False (test failure) | test_failure | test_failure |
| HumanEval/20 | False (compilation issue) | True | compilation_error | pass |
| HumanEval/24 | True | True | pass | pass |
| HumanEval/60 | True | True | pass | pass |
| HumanEval/62 | False (compilation issue) | True | compilation_error | pass |
| HumanEval/67 | False (test failure) | False (compilation issue) | test_failure | compilation_error |
| HumanEval/75 | True | False (compilation issue) | pass | compilation_error |
| HumanEval/77 | False (compilation issue) | True | compilation_error | pass |
| HumanEval/79 | True | True | pass | pass |
| HumanEval/81 | True | True | pass | pass |
| HumanEval/102 | True | True | pass | pass |
| HumanEval/118 | True | True | pass | pass |
| HumanEval/120 | False (compilation issue) | True | compilation_error | pass |
| HumanEval/126 | True | True | pass | pass |
| HumanEval/129 | False (compilation issue) | False (test failure) | compilation_error | test_failure |
| HumanEval/136 | False (compilation issue) | False (test failure) | compilation_error | test_failure |
| HumanEval/140 | True | True | pass | pass |
| HumanEval/145 | False (test failure) | False (test failure) | test_failure | test_failure |
| HumanEval/148 | False (test failure) | True | test_failure | pass |
| HumanEval/161 | False (compilation issue) | True | compilation_error | pass |

## Task 2 - Bug detection

- Vanilla success rate: 10.0% (2/20)
- Crafted success rate: 75.0% (15/20)
- Absolute improvement: +65.0 percentage points
- Rubric check: **EXCEEDS EXPECTED RANGE - document the improvement and methodology**
- Vanilla outcomes: correct_buggy_prediction: 2, parse_error: 14, predicted_correct: 4
- Crafted outcomes: correct_buggy_prediction: 15, predicted_correct: 5

| Task ID | Vanilla | Crafted |
|---|---:|---:|
| HumanEval/60 | False | True |
| HumanEval/24 | True | True |
| HumanEval/67 | False | True |
| HumanEval/145 | False | False |
| HumanEval/129 | False | True |
| HumanEval/77 | False | False |
| HumanEval/79 | False | True |
| HumanEval/20 | False | True |
| HumanEval/62 | False | False |
| HumanEval/102 | False | True |
| HumanEval/8 | False | False |
| HumanEval/81 | False | True |
| HumanEval/140 | False | False |
| HumanEval/161 | False | True |
| HumanEval/136 | False | True |
| HumanEval/75 | True | True |
| HumanEval/148 | False | True |
| HumanEval/118 | False | True |
| HumanEval/126 | False | True |
| HumanEval/120 | False | True |
