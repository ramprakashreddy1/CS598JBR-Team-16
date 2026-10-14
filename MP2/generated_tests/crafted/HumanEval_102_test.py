import pytest
from HumanEval_102 import *

import pytest
from HumanEval_102 import *


# ---- additional tests from coverage feedback ----
import pytest
from HumanEval_102 import *

import pytest
from HumanEval_102 import choose_num

def test_choose_num_x_greater_than_y_extra():
    assert choose_num(5, 3) == -1

def test_choose_num_y_is_even_extra():
    assert choose_num(3, 10) == 10

def test_choose_num_x_equals_y_extra():
    assert choosenum(5, 5) == -1

def test_choose_num_y_is_odd_extra():
    assert choose_num(3, 9) == 7

def test_choose_num_x_less_than_y_extra():
    assert choose_num(1, 10) == 8
