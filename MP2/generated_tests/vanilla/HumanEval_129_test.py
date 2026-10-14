import pytest
from HumanEval_129 import *

import pytest
from HumanEval_129 import *

def test_minPath():
    # Test case 1:
    grid = [[0, 1, 0], [0, 0, 1], [1, 0, 0]]
    k = 5
    assert minPath(grid, k) == [1, 1, 1, 1, 1]

    # Test case 2:
    grid = [[0, 1, 1], [1, 0, 1], [1, 1, 0]]
    k = 5
    assert minPath(grid, k) == [1, 1, 1, 1, 1]

    # Test case 3:
    grid = [[0, 1, 0, 1], [1, 0, 1, 0], [0, 1, 0, 1], [1, 0, 1, 0]]
    k = 7
    assert minPath(grid, k) == [1, 1, 1, 1, 1, 1, 1]

    # Test case 4:
    grid = [[1, 1, 1, 1], [1, 1, 1, 1], [1, 1, 1, 1], [1, 1, 1, 1]]
    k = 3
    assert minPath(grid, k) == [1, 1, 1]

    # Test case 5:
    grid = [[0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 1]]
    k = 4
    assert minPath(grid, k) == [1, 1, 1, 1]
