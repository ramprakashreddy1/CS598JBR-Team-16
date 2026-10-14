import pytest
from HumanEval_140 import *

import pytest
from HumanEval_140 import *


# ---- additional tests from coverage feedback ----
import pytest
from HumanEval_140 import *

import pytest
from HumanEval_140 import fix_spaces

def test_fix_spaces_no_spaces_extra():
    assert fix_spaces("Example") == "Example"

def test_fix_spaces_one_space_extra():
    assert fix_spaces("Example 1") == "Example_1"

def test_fix_spaces_leading_space_extra():
    assert fix_spaces(" Example 2") == "_Example_2"

def test_fix_spaces_multiple_spaces_extra():
    assert fix_spaces(" Example   3") == "_Example-3"

def test_fix_spaces_multiple_spaces_at_end_extra():
    assert fix_spaces("Example 3   ") == "Example_3_"

def test_fix_spaces_multiple_spaces_at_start_extra():
    assert fix_spaces("   Example 3") == "_Example_3"

def test_fix_spaces_multiple_spaces_in_middle_extra():
    assert fix_spaces("Example  1") == "Example_1"

def test_fix_spaces_multiple_spaces_in_middle_and_end_extra():
    assert fix_spaces("Example 1   ") == "Example_1_"

def test_fix_spaces_multiple_spaces_in_middle_and_start_extra():
    assert fix_spaces("   Example 1") == "_Example_1"
