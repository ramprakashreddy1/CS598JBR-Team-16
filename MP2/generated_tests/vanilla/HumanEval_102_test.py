import pytest
from HumanEval_102 import *

import pytest










def test_choose_num():
    assert choose_num(5, 6) == 6
    assert choose_num(3, 4) == 3
    assert choose_num(2, 2) == -1
    assert choose_num(10, 12) == 11
    assert choose_num(7, 7) == -1
    assert choose_num(15, 15) == -1
    assert choose_num(9, 8) == 7
    assert choose_num(11, 9) == 8
