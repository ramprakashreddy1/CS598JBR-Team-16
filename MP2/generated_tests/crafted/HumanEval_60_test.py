import pytest
from HumanEval_60 import *

import pytest
from HumanEval_60 import *

@pytest.mark.parametrize("n, expected", [
    (30, 465),
    (100, 5050),
    (5, 15),
    (10, 55),
    (1, 1),
    (0, 0),
    (-5, 0),
    (1000, 500500),
    (10000, 50005000),
    (100000, 5000050000),
])
def test_sum_to_n(n, expected):
    assert sum_to_n(n) == expected

def test_sum_to_n_negative():
    assert sum_to_n(-10) == 0

def test_sum_to_n_empty():
    assert sum_to_n(0) == 0

def test_sum_to_n_single():
    assert sum_to_n(1) == 1

def test_sum_to_n_zero():
    assert sum_to_n(0) == 0

def test_sum_to_n_boundary():
    assert sum_to_n(1000000) == 5000005000000
