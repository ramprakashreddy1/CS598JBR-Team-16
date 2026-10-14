import pytest
from HumanEval_161 import *

import pytest
from HumanEval_161 import *

def test_solve():
    assert solve("1234") == "4321"
    assert solve("ab") == "AB"
    assert solve("#a@C") == "#A@c"
    assert solve("") == ""
    assert solve("A") == "a"
    assert solve("a") == "A"
    assert solve("1234567890") == "0987654321"
    assert solve("!@#$%^&*()") == "!@#$%^&*()"
    assert solve("aBcDeFgHi") == "AbCdEfGhI"
    assert solve("ABCDEFGHI") == "abcdefghi"
    assert solve("!@#123") == "!@#123"
    assert solve("!@#AbC") == "!@#aBc"
    assert solve("!1@2#3$") == "!1@2#3$"
    assert solve("!@#aBc123") == "!@#AbC123"
    assert solve("!1@2#3$aBc") == "!1@2#3$AbC"
    assert solve("!1@2#3$AbC123") == "!1@2#3$aBc123"
    assert solve("!1@2#3$AbC123$") == "$3@2#1!aBc123"
