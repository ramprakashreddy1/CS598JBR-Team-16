import pytest
from HumanEval_126 import *

import pytest
from HumanEval_126 import *

def test_is_sorted():
    assert is_sorted([1, 2, 3, 4, 5]) == True
    assert is_sorted([5, 4, 3, 2, 1]) == False
    assert is_sorted([1, 2, 2, 3, 4]) == True
    assert is_sorted([1, 2, 3, 2, 4]) == False
    assert is_sorted([1, 1, 2, 2, 3]) == True
    assert is_sorted([1, 2, 2, 2, 3]) == True
    assert is_sorted([1, 2, 3, 3, 4]) == True
    assert is_sorted([1, 2, 3, 3, 5]) == True
    assert is_sorted([5, 5, 5, 5, 5]) == True
    assert is_sorted([1, 1, 1, 1, 1]) == True
    assert is_sorted([1, 2, 2, 2, 2]) == True
    assert is_sorted([2, 2, 2, 2, 2]) == True
    assert is_sorted([1, 2, 3, 3, 2]) == False
    assert is_sorted([1, 2, 2, 3, 2]) == False
    assert is_sorted([1, 2, 3, 2, 2]) == False
    assert is_sorted([1, 2, 2, 2, 1]) == False
    assert is_sorted([1, 1, 1, 2, 2]) == True
    assert is_sorted([1, 1, 1, 1, 2]) == True
    assert is_sorted([1, 1, 1, 1, 1]) == True
    assert is_sorted([1, 2, 2, 2, 1]) == False
    assert is_sorted([1, 2, 2, 1, 1]) == False
    assert is_sorted([1, 2, 1, 1, 1]) == False
    assert is_sorted([1, 1, 1, 2, 1]) == False
    assert is_sorted([1, 1, 2, 2, 1]) == False
    assert is_sorted([1, 1, 2, 1, 1]) == False
    assert is_sorted([1, 1, 1, 2, 2]) == True
    assert is_sorted([1, 1, 1, 1, 2]) == True
    assert is_sorted([1, 1, 1, 1, 1]) == True
