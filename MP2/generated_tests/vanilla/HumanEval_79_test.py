import pytest
from HumanEval_79 import *

import pytest
from HumanEval_79 import *

def test_decimal_to_binary():
    assert decimal_to_binary(0) == "db0db"
    assert decimal_to_binary(1) == "db1db"
    assert decimal_to_binary(2) == "db10db"
    assert decimal_to_binary(3) == "db11db"
    assert decimal_to_binary(10) == "db1010db"
    assert decimal_to_binary(255) == "db1111111db"
    assert decimal_to_binary(-1) == "db-1db"  # negative numbers are handled
