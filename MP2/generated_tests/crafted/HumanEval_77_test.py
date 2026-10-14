import pytest
from HumanEval_77 import *

import pytest
from HumanEval_77 import iscube

def test_iscube():
    # Test with positive integers
    assert iscube(1) == True
    assert iscube(2) == False
    assert iscube(64) == True
    assert iscube(0) == True
    assert iscube(180) == False

    # Test with negative integers
    assert iscube(-1) == True
    assert iscube(-64) == True
    assert iscube(-180) == False

    # Test with boundary values
    assert iscube(8) == True
    assert iscube(27) == True
    assert iscube(28) == False

    # Test with largest and smallest cases
    assert iscube(125873) == True
    assert iscube(125874) == False

    # Test with edge cases
    assert iscube(0) == True
    assert iscube(1) == True
    assert iscube(-1) == True
