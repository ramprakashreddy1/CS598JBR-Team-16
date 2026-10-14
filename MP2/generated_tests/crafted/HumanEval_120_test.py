import pytest
from HumanEval_120 import *

import pytest
from HumanEval_120 import *


# ---- additional tests from coverage feedback ----
import pytest
from HumanEval_120 import *

from HumanEval_120 import *

def test_maximum_k_is_zero_extra():
    assert maximum([], 0) == []
    assert maximum([1, 2, 3, 4, 5], 0) == []
    assert maximum([-1, -2, -3, -4, -5], 0) == []

def test_maximum_k_is_one_extra():
    assert maximum([1, 2, 3, 4, 5], 1) == [5]
    assert maximum([-1, -2, -3, -4, -5], 1) == [-1]
    assert maximum([1, 2, 3, 4, 5], 1) == [5]

def test_maximum_k_is_len_of_array_extra():
    assert maximum([1, 2, 3, 4, 5], 5) == [1, 2, 3, 4, 5]
    assert maximum([-1, -2, -3, -4, -5], 5) == [-1, -2, -3, -4, -5]

def test_maximum_k_is_middle_of_array_extra():
    assert maximum([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 5) == [6, 7, 8, 9, 10]
    assert maximum([10, 9, 8, 7, 6, 5, 4, 3, 2, 1], 5) == [10, 9, 8, 7, 6]

def test_maximum_k_is_greater_than_len_of_array_extra():
    assert maximum([1, 2, 3, 4, 5], 6) == [1, 2, 3, 4, 5]
    assert maximum([-1, -2, -3, -4, -5], 6) == [-1, -2, -3, -4, -5]
