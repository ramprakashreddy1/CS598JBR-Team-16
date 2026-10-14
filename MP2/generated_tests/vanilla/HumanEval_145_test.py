import pytest
from HumanEval_145 import *

import pytest
from HumanEval_145 import *

def test_order_by_points():
    assert order_by_points([15, 20, -30, 45]) == [-30, 15, 20, 45]
    assert order_by_points([10, 200, 3000, -4000]) == [10, 200, 3000, -4000]
    assert order_by_points([0, 1, 2, 3, 4, 5]) == [0, 1, 2, 3, 4, 5]
    assert order_by_points([12, 21, 32, 43, 54, 65]) == [12, 21, 32, 43, 54, 65]
    assert order_by_points([-1, -2, -3, -4, -5, -6]) == [-1, -2, -3, -4, -5, -6]
    assert order_by_points([-10, 2, -30, 4]) == [-30, 2, -10, 4]
    assert order_by_points([100, 2, 30, 4]) == [4, 2, 30, 100]
