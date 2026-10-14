import pytest
from HumanEval_62 import *

import pytest
from HumanEval_62 import *

def test_derivative_empty():
    assert derivative([]) == []

def test_derivative_single_element():
    assert derivative([3]) == []

def test_derivative_multiple_elements():
    assert derivative([1, 2, 3, 4]) == [(1, 2), (2, 6), (3, 12)]

def test_derivative_negative_elements():
    assert derivative([-1, -2, -3, -4]) == [(1, -2), (2, -6), (3, -12)]

def test_derivative_mixed_elements():
    assert derivative([1, -2, 3, -4]) == [(1, -2), (2, 6), (3, -12)]
