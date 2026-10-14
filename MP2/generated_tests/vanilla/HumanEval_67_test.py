import pytest
from HumanEval_67 import *

import pytest
from HumanEval_67 import *

def test_fruit_distribution():
    assert fruit_distribution("10 20 30", 100) == 0
    assert fruit_distribution("10 20 30", 200) == 40
    assert fruit_distribution("10 20 30", 300) == 60
    assert fruit_distribution("10 20 30", 400) == 70
    assert fruit_distribution("10 20 30", 500) == 80
    assert fruit_distribution("10 20 30", 600) == 90
    assert fruit_distribution("10 20 30", 700) == 100
    assert fruit_distribution("10 20 30", 800) == 110
    assert fruit_distribution("10 20 30", 900) == 120
    assert fruit_distribution("10 20 30", 1000) == 130
