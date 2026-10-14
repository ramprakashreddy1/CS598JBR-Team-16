import pytest
from HumanEval_60 import *

import pytest




def test_sum_to_n():
    assert sum_to_n(0) == 0
    assert sum_to_n(1) == 1
    assert sum_to_n(5) == 15
    assert sum_to_n(10) == 55
