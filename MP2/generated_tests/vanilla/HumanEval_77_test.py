import pytest
from HumanEval_77 import *

import pytest
from HumanEval_77 import *

def test_iscube_positive():
    assert iscube(8) == True
    assert iscube(27) == True
    assert iscube(1) == True

def test_iscube_negative():
    assert iscube(-8) == True
    assert iscube(-27) == True
    assert iscube(-1) == True

def test_iscube_non_cubes():
    assert iscube(9) == False
    assert iscube(25) == False
    assert iscube(0) == False
    assert iscube(-9) == False
    assert iscube(-25) == False
