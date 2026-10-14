import pytest
from HumanEval_129 import *

import pytest
from HumanEval_129 import minPath

def test_minPath():
    # Test with empty grid
    assert minPath([[]], 1) == []

    # Test with single element
    assert minPath([[1]], 1) == [1]

    # Test with zero
    assert minPath([[0]], 1) == [0]

    # Test with negative numbers
    assert minPath([[-1]], 1) == [-1]

    # Test with boundary values
    assert minPath([[1, 2]], 1) == [1]
    assert minPath([[1], [2]], 1) == [1]

    # Test with largest/smallest cases
    assert minPath([[1, 2], [3, 4]], 2) == [1, 2]
    assert minPath([[4, 3], [2, 1]], 2) == [1, 2]

    # Test with examples from docstring
    assert minPath([[1, 2, 3], [4, 5, 6], [7, 8, 9]], 3) == [1, 2, 1]
    assert minPath([[5, 9, 3], [4, 1, 6], [7, 8, 2]], 1) == [1]

    # Test with parametrized inputs
    grid = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
    k = 3
    assert minPath(grid, k) == [1, 2, 1]

    grid = [[5, 9, 3], [4, 1, 6], [7, 8, 2]]
    k = 1
    assert minPath(grid, k) == [1]

    # Test with larger inputs
    grid = [[i for i in range(1, 101)] for _ in range(100)]
    k = 100
    assert minPath(grid, k) == [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]


# ---- additional tests from coverage feedback ----
import pytest
from HumanEval_129 import *

from HumanEval_129 import minPath

def test_minPath_1_extra():
    grid = [[1,2,3], [4,5,6], [7,8,9]]
    k = 3
    assert minPath(grid, k) == [1, 2, 1]

def test_minPath_2_extra():
    grid = [[5,9,3], [4,1,6], [7,8,2]]
    k = 1
    assert minPath(grid, k) == [1]

def test_minPath_3_extra():
    grid = [[1,2,3], [4,5,6], [7,8,9]]
    k = 1
    assert minPath(grid, k) == [1]

def test_minPath_4_extra():
    grid = [[1,2,3], [4,5,6], [7,8,9]]
    k = 2
    assert minPath(grid, k) == [1, 2]

def test_minPath_5_extra():
    grid = [[1,2,3], [4,5,6], [7,8,9]]
    k = 4
    assert minPath(grid, k) == [1, 2, 1, 2]
