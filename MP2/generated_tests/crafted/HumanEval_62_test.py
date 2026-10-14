import pytest
from HumanEval_62 import *

import pytest
from HumanEval_62 import *

def test_derivative():
    # Test with empty list
    assert derivative([]) == []

    # Test with single element
    assert derivative([1]) == []

    # Test with zero
    assert derivative([0, 1, 2, 3]) == [1, 4]

    # Test with negative numbers
    assert derivative([-1, 1, 2, 3]) == [1, 4]

    # Test with boundary values
    assert derivative([1, 2, 3, 4, 5]) == [2, 6, 12]

    # Test with largest and smallest cases
    assert derivative([1, 2, 3, 4, 5, 6, 7, 8, 9, 10]) == [2, 6, 12, 20, 30]

    # Test with examples from the docstring
    assert derivative([3, 1, 2, 4, 5]) == [1, 4, 12, 20]
    assert derivative([1, 2, 3]) == [2, 6]

    # Test with parametrized inputs
    inputs = [[1, 2, 3, 4, 5], [2, 3, 4, 5], [0, 1, 2, 3], [-1, 1, 2, 3], [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]]
    expected = [[2, 6, 12, 20], [3, 8, 15], [2, 6], [1, 4], [2, 6, 12, 20, 30]]
    for input, expected in zip(inputs, expected):
        assert derivative(input) == expected
