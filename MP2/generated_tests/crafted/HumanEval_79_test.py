import pytest
from HumanEval_79 import *

import pytest
from HumanEval_79 import decimal_to_binary

class TestDecimalToBinary:
    @pytest.mark.parametrize("decimal, expected", [
        (15, "db1111db"),
        (32, "db100000db"),
        (0, "db0db"),
        (1, "db1db"),
        (2, "db10db"),
        (3, "db11db"),
        (4, "db100db"),
        (5, "db101db"),
        (6, "db110db"),
        (7, "db111db"),
        (8, "db1000db"),
        (9, "db1001db"),
        (10, "db1010db"),
        (150, "db1001010db"),
        (255, "db1111111db"),
        (256, "db10000000db"),
        (-1, "db-1db"),
        (-2, "db-10db"),
        (-3, "db-11db"),
        (-4, "db-100db"),
        (-5, "db-101db"),
        (-6, "db-110db"),
        (-7, "db-111db"),
        (-8, "db-1000db"),
        (-9, "db-1001db"),
        (-10, "db-1010db"),
        (-150, "db-1001010db"),
        (-255, "db-1111111db"),
        (-256, "db-10000000db"),
    ])
    def test_decimal_to_binary(self, decimal, expected):
        assert decimal_to_binary(decimal) == expected
