## MP2-Task1: is_correct per program

| Task ID | Input | Expected | Vanilla | Crafted |
|---|---|---|---|---|
| HumanEval/60 | `1` | `1` | True | True |
| HumanEval/24 | `49` | `7` | False | False |
| HumanEval/67 | `"5 apples and 6 oranges", 19` | `8` | False | False |
| HumanEval/145 | `[1234,423,463,145,2,423,423,53,6,37,3457` | `[0, 2, 3, 6, 53, 423, 423, 423` | False | False |
| HumanEval/129 | `[[1, 2, 3], [4, 5, 6], [7, 8, 9]], 3` | `[1, 2, 1]` | False | True |
| HumanEval/77 | `1` | `True` | True | True |
| HumanEval/79 | `15` | `'db1111db'` | True | True |
| HumanEval/20 | `[1.0, 2.0, 3.9, 4.0, 5.0, 2.2]` | `(3.9, 4.0)` | False | False |
| HumanEval/62 | `[3, 1, 2, 4, 5]` | `[1, 4, 12, 20]` | False | True |
| HumanEval/102 | `12, 15` | `14` | True | True |
| HumanEval/8 | `[]` | `(0, 1)` | True | True |
| HumanEval/81 | `[1, 0.3, 1.5, 2.8, 3.3]` | `['D', 'D-', 'C-', 'B', 'B+']` | False | False |
| HumanEval/140 | `"Yellow Yellow  Dirty  Fellow"` | `'Yellow_Yellow__Dirty__Fellow'` | False | False |
| HumanEval/161 | `"ab"` | `'AB'` | True | True |
| HumanEval/136 | `[-1, -3, -5, -6]` | `(-1, None)` | False | True |
| HumanEval/75 | `30` | `True` | True | True |
| HumanEval/148 | `"Neptune", "Venus"` | `('Earth', 'Mars', 'Jupiter', '` | False | False |
| HumanEval/118 | `"ab"` | `''` | False | True |
| HumanEval/126 | `[5]` | `True` | True | True |
| HumanEval/120 | `[4, -4, 4], 2` | `[4, 4]` | True | True |

Success rate: vanilla 9/20 = 45%, crafted 13/20 = 65%, absolute improvement +20 points

## MP2-Task2: generated tests (vanilla)

| Task ID | Total tests | Passed | Failed | Pass % |
|---|---|---|---|---|
| HumanEval/60 | 1 | 1 | 0 | 100% |
| HumanEval/24 | 1 | 0 | 1 | 0% |
| HumanEval/67 | 1 | 0 | 1 | 0% |
| HumanEval/145 | 1 | 0 | 1 | 0% |
| HumanEval/129 | 1 | 0 | 1 | 0% |
| HumanEval/77 | 3 | 2 | 1 | 67% |
| HumanEval/79 | 1 | 0 | 1 | 0% |
| HumanEval/20 | 1 | 0 | 1 | 0% |
| HumanEval/62 | 5 | 2 | 3 | 40% |
| HumanEval/102 | 1 | 0 | 1 | 0% |
| HumanEval/8 | 1 | 0 | 1 | 0% |
| HumanEval/81 | 1 | 0 | 1 | 0% |
| HumanEval/140 | 1 | 0 | 1 | 0% |
| HumanEval/161 | 1 | 0 | 1 | 0% |
| HumanEval/136 | 1 | 0 | 1 | 0% |
| HumanEval/75 | 1 | 0 | 1 | 0% |
| HumanEval/148 | 3 | 2 | 1 | 67% |
| HumanEval/118 | 1 | 0 | 1 | 0% |
| HumanEval/126 | 1 | 0 | 1 | 0% |
| HumanEval/120 | 1 | 0 | 1 | 0% |
| **Total** | 28 | 7 | 21 | 25.0% |

## MP2-Task2: generated tests (crafted)

| Task ID | Total tests | Passed | Failed | Pass % |
|---|---|---|---|---|
| HumanEval/60 | 15 | 14 | 1 | 93% |
| HumanEval/24 | 28 | 25 | 3 | 89% |
| HumanEval/67 | 1 | 0 | 1 | 0% |
| HumanEval/145 | 1 | 0 | 1 | 0% |
| HumanEval/129 | 6 | 5 | 1 | 83% |
| HumanEval/77 | 1 | 0 | 1 | 0% |
| HumanEval/79 | 29 | 13 | 16 | 45% |
| HumanEval/20 | 5 | 5 | 0 | 100% |
| HumanEval/62 | 1 | 0 | 1 | 0% |
| HumanEval/102 | 5 | 2 | 3 | 40% |
| HumanEval/8 | 17 | 8 | 9 | 47% |
| HumanEval/81 | 28 | 18 | 10 | 64% |
| HumanEval/140 | 9 | 4 | 5 | 44% |
| HumanEval/161 | 1 | 0 | 1 | 0% |
| HumanEval/136 | 1 | 0 | 1 | 0% |
| HumanEval/75 | 104 | 83 | 21 | 80% |
| HumanEval/148 | 7 | 6 | 1 | 86% |
| HumanEval/118 | 13 | 10 | 3 | 77% |
| HumanEval/126 | 44 | 38 | 6 | 86% |
| HumanEval/120 | 5 | 2 | 3 | 40% |
| **Total** | 321 | 233 | 88 | 72.6% |

## MP2-Task2: coverage per program

| Task ID | Vanilla coverage (%) | Crafted coverage (%) |
|---|---|---|
| HumanEval/60 | 100.0 | 100.0 |
| HumanEval/24 | 100.0 | 100.0 |
| HumanEval/67 | 100.0 | 100.0 |
| HumanEval/145 | 100.0 | 100.0 |
| HumanEval/129 | 100.0 | 100.0 |
| HumanEval/77 | 100.0 | 100.0 |
| HumanEval/79 | 100.0 | 100.0 |
| HumanEval/20 | 100.0 | 100.0 |
| HumanEval/62 | 100.0 | 100.0 |
| HumanEval/102 | 50.0 | 87.5 |
| HumanEval/8 | 100.0 | 100.0 |
| HumanEval/81 | 27.59 | 100.0 |
| HumanEval/140 | 84.21 | 94.74 |
| HumanEval/161 | 100.0 | 100.0 |
| HumanEval/136 | 100.0 | 100.0 |
| HumanEval/75 | 100.0 | 100.0 |
| HumanEval/148 | 88.89 | 100.0 |
| HumanEval/118 | 100.0 | 100.0 |
| HumanEval/126 | 100.0 | 100.0 |
| HumanEval/120 | 100.0 | 100.0 |
| **Average** | 92.53 | 99.11 |

## Correlation: code reasoning (Task 1) vs. passing tests (Task 2)

- vanilla: point-biserial r(is_correct, test pass rate) = 0.152; phi(is_correct, all tests pass) = 0.254
- crafted: point-biserial r(is_correct, test pass rate) = -0.122; phi(is_correct, all tests pass) = -0.313
