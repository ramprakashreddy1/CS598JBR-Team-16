import pytest
from HumanEval_24 import *

import pytest
from HumanEval_24 import *

@pytest.mark.parametrize("n, expected", [
    (15, 5),
    (1, 1),
    (0, 0),
    (-5, -1),
    (13, 1),
    (100, 50),
    (1000, 500),
    (10000, 5000),
    (100000, 50000),
    (2, 1),
    (3, 1),
    (4, 2),
    (5, 1),
    (6, 3),
    (7, 1),
    (8, 4),
    (9, 3),
    (10, 5),
    (11, 1),
    (12, 6),
    (13, 1),
    (14, 7),
    (15, 5),
    (16, 8),
    (17, 1),
    (18, 9),
    (19, 1),
    (20, 10),
])
def test_largest_divisor(n, expected):
    assert largest_divisor(n) == expected
