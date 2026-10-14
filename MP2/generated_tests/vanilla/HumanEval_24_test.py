import pytest
from HumanEval_24 import *

import pytest
from HumanEval_24 import *

def test_largest_divisor():
    assert largest_divisor(10) == 5
    assert largest_divisor(17) == 17
    assert largest_divisor(24) == 8
    assert largest_divisor(13) == 13
    assert largest_divisor(100) == 50
