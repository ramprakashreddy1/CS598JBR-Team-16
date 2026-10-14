import pytest
from HumanEval_140 import *

import pytest
from HumanEval_140 import *

def test_fix_spaces():
    assert fix_spaces("") == ""
    assert fix_spaces("a") == "a"
    assert fix_spaces("hi there") == "hi_there"
    assert fix_spaces("how are you") == "how_are_you"
    assert fix_spaces("I am fine") == "I_am_fine"
    assert fix_spaces("I'm fine") == "I'm_fine"
    assert fix_spaces("I'm  fine") == "I'm--fine"
    assert fix_spaces("I'm   fine") == "I'm---fine"
