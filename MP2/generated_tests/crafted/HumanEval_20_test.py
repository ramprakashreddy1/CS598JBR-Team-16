import pytest
from HumanEval_20 import *

import pytest
from HumanEval_20 import *


# ---- additional tests from coverage feedback ----
import pytest
from HumanEval_20 import *

import pytest
from HumanEval_20 import find_closest_elements

def test_find_closest_elements_1_extra():
    assert find_closest_elements([1.0, 2.0, 3.0, 4.0, 5.0, 2.2]) == (2.0, 2.2)

def test_find_closest_elements_2_extra():
    assert find_closest_elements([1.0, 2.0, 3.0, 4.0, 5.0, 2.0]) == (2.0, 2.0)

def test_find_closest_elements_3_extra():
    assert find_closest_elements([1.0, 2.0, 3.0, 4.0, 5.0, 6.0]) == (1.0, 2.0)

def test_find_closest_elements_4_extra():
    assert find_closest_elements([1.0, 2.0, 3.0, 4.0, 5.0, 0.5]) == (0.5, 1.0)

def test_find_closest_elements_5_extra():
    assert find_closest_elements([1.0, 2.0, 3.0, 4.0, 5.0, 1.5]) == (1.0, 1.5)
