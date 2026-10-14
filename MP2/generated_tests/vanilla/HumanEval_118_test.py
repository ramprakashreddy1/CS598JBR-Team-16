import pytest
from HumanEval_118 import *

import pytest
from HumanEval_118 import *

def test_get_closest_vowel():
    assert get_closest_vowel("") == ""
    assert get_closest_vowel("bcd") == ""
    assert get_closest_vowel("abc") == ""
    assert get_closest_vowel("bcdfgh") == ""
    assert get_closest_vowel("bcdEfgh") == "E"
    assert get_closest_vowel("bcdEfghI") == ""
    assert get_closest_vowel("bcdEfghiI") == "i"
    assert get_closest_vowel("bcdEfghiO") == "O"
    assert get_closest_vowel("bcdEfghiU") == ""
    assert get_closest_vowel("bcdEfghiOo") == "O"
    assert get_closest_vowel("bcdEfghiUu") == ""
    assert get_closest_vowel("bcdEfghiUuo") == "o"
