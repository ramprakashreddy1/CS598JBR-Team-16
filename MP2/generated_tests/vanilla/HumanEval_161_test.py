import pytest
from HumanEval_161 import *

import pytest
from HumanEval_161 import *

def test_solve():
    assert solve("Hello") == "hELLO"
    assert solve("Python") == "pYTHON"
    assert solve("1234") == "1234"
    assert solve("") == ""
    assert solve("UPPER") == "lower"
    assert solve("lower") == "UPPER"
    assert solve("Hello World!") == "hELLO wORLD!"
    assert solve("123456") == "123456"
    assert solve("1234567890") == "1234567890"
