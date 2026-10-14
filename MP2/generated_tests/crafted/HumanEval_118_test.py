import pytest
from HumanEval_118 import *

import pytest
from HumanEval_118 import get_closest_vowel

def test_get_closest_vowel():
    # Test with empty string
    assert get_closest_vowel("") == ""

    # Test with single character string
    assert get_closest_vowel("a") == ""

    # Test with two characters string
    assert get_closest_vowel("ae") == ""

    # Test with three characters string
    assert get_closest_vowel("aer") == ""

    # Test with four characters string
    assert get_closest_vowel("aerh") == "e"

    # Test with five characters string
    assert get_closest_vowel("aerhi") == "e"

    # Test with six characters string
    assert get_closest_vowel("aerhil") == ""

    # Test with seven characters string
    assert get_closest_vowel("aerhili") == "i"

    # Test with eight characters string
    assert get_closest_vowel("aerhilic") == ""

    # Test with all vowels
    assert get_closest_vowel("aeiouAEIOU") == ""

    # Test with all consonants
    assert get_closest_vowel("bcdfghjklmnpqrstvwxyzBCDFGHJKLMNPQRSTVWXYZ") == ""

    # Test with a mix of vowels and consonants
    assert get_closest_vowel("bcdfghjklmnpqrstvwxyzBCDFGHJKLMNPQRSTVWXYZbcdfghjklmnpqrstvwxyzBCDFGHJKLMNPQRSTVWXYZ") == ""

    # Test with a mix of vowels and consonants with a vowel in the middle
    assert get_closest_vowel("bcdfghjklmnpqrstvwxyzBCDFGHJKLMNPQRSTVWXYZe") == "e"

    # Test with a mix of vowels and consonants with a vowel at the end
    assert get_closest_vowel("bcdfghjklmnpqrstvwxyzBCDFGHJKLMNPQRSTVWXYZe") == "e"

    # Test with a mix of vowels and consonants with a vowel at the beginning
    assert get_closest_vowel("e") == ""

    # Test with a mix of vowels and consonants with a vowel at the beginning and end
    assert get_closest_vowel("e") == ""

    # Test with a mix of vowels and consonants with a vowel in the middle and at the beginning and end
    assert get_closest_vowel("bcdfghjklmnpqrstvwxyzBCDFGHJKLMNPQRSTVWXYZe") == "e"


# ---- additional tests from coverage feedback ----
import pytest
from HumanEval_118 import *

import pytest
from HumanEval_118 import get_closest_vowel

def test_get_closest_vowel_1_extra():
    assert get_closest_vowel("yogurt") == "u"

def test_get_closest_vowel_2_extra():
    assert get_closest_vowel("FULL") == "U"

def test_get_closest_vowel_3_extra():
    assert get_closest_vowel("quick") == ""

def test_get_closest_vowel_4_extra():
    assert get_closest_vowel("ab") == ""

def test_get_closest_vowel_5_extra():
    assert get_closest_vowel("Yogurt") == "u"

def test_get_closest_vowel_6_extra():
    assert get_closest_vowel("FuLl") == "U"

def test_get_closest_vowel_7_extra():
    assert get_closest_vowel("quick") == ""

def test_get_closest_vowel_8_extra():
    assert get_closest_vowel("ab") == ""

def test_get_closest_vowel_9_extra():
    assert get_closest_vowel("YOGURT") == "u"

def test_get_closest_vowel_10_extra():
    assert get_closest_vowel("FULL") == "U"

def test_get_closest_vowel_11_extra():
    assert get_closest_vowel("QUICK") == ""

def test_get_closest_vowel_12_extra():
    assert get_closest_vowel("AB") == ""
