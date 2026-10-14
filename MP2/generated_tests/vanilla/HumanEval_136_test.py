import pytest
from HumanEval_136 import *

import pytest
from HumanEval_136 import *

def test_largest_smallest_integers():
    assert largest_smallest_integers([1, 2, 3, -4, -5, 6]) == (-5, 1)
    assert largest_smallest_integers([10, 20, 30, -40, -50, 60]) == (-50, 10)
    assert largest_smallest_integers([-1, -2, -3, -4, -5, -6]) == (-1, None)
    assert largest_smallest_integers([1, 2, 3, 4, 5, 6]) == (None, 1)
    assert largest_smallest_integers([]) == (None, None)
