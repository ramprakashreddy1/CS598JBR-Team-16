import pytest
from HumanEval_145 import *

import pytest
from HumanEval_145 import *

def test_order_by_points():
    assert order_by_points([1, 11, -1, -11, -12]) == [-1, -11, 1, -12, 11]
    assert order_by_points([]) == []
    assert order_by_points([0]) == [0]
    assert order_by_points([-1, 1]) == [-1, 1]
    assert order_by_points([12, 2]) == [2, 12]
    assert order_by_points([111, 22]) == [22, 111]
    assert order_by_points([111, -22]) == [-22, 111]
    assert order_by_points([111, 222]) == [111, 222]
    assert order_by_points([111, -222]) == [-222, 111]
    assert order_by_points([111, 222, 333]) == [111, 222, 333]
    assert order_by_points([111, -222, 333]) == [-222, 111, 333]
    assert order_by_points([111, 222, -333]) == [-333, 111, 222]
    assert order_by_points([111, -222, -333]) == [-222, -333, 111]
    assert order_by_points([111, 222, 333, -444]) == [-444, 111, 222, 333]
    assert order_by_points([111, -222, 333, -444]) == [-222, -444, 111, 333]
    assert order_by_points([111, 222, -333, -444]) == [-333, -444, 111, 222]
    assert order_by_points([111, -222, -333, -444]) == [-222, -333, -444, 111]
