import pytest
from HumanEval_8 import *

import pytest
from HumanEval_8 import sum_product


@pytest.mark.parametrize("numbers, expected", [
    ([], (0, 1)),
    ([1, 2, 3, 4], (10, 24)),
    ([0, 1, 2, 3, 4], (10, 24)),
    ([-1, 1], (-1, -1)),
    ([2, 3, 4], (9, 24)),
    ([5, 6, 7, 8], (26, 1680)),
    ([100, 200, 300, 400], (1000, 2400000)),
    ([-10, -20, -30, -40], (-100, -2400)),
    ([1000, 2000, 3000, 4000], (10000, 24000000)),
    ([-1000, -2000, -300, -4000], (-10000, -24000000)),
    ([10000, 20000, 30000, 40000], (100000, 2400000000)),
])
def test_sum_product(numbers, expected):
    assert sum_product(numbers) == expected


def test_empty_input():
    assert sum_product([]) == (0, 1)


def test_single_element():
    assert sum_product([5]) == (5, 5)


def test_zero():
    assert sum_product([0, 1, 2, 3]) == (6, 0)


def test_negative_numbers():
    assert sum_product([-1, -2, -3, -4]) == (-10, 24)


def test_boundary_values():
    assert sum_product([1000000, 2000000, 3000000, 4000000]) == (10000000, 2400000000000)


def test_largest_smallest_cases():
    assert sum_product([-1000000, 1000000]) == (0, 0)
