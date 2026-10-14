import pytest
from HumanEval_120 import *

import pytest
from HumanEval_120 import *

def test_maximum():
    assert maximum([1, 2, 3, 4, 5], 2) == [4, 5]
    assert maximum([1, 2, 3, 4, 5], 3) == [3, 4, 5]
    assert maximum([1, 2, 3, 4, 5], 5) == [1, 2, 3, 4, 5]
    assert maximum([1, 2, 3, 4, 5], 0) == []
    assert maximum([5, 4, 3, 2, 1], 2) == [4, 5]
    assert maximum([5, 4, 3, 2, 1], 3) == [3, 4, 5]
    assert maximum([5, 4, 3, 2, 1], 5) == [1, 2, 3, 4, 5]
    assert maximum([5, 4, 3, 2, 1], 0) == []
    assert maximum([1, 1, 2, 2, 3], 2) == [2, 3]
    assert maximum([1, 1, 2, 2, 3], 3) == [1, 2, 3]
    assert maximum([1, 1, 2, 2, 3], 5) == [1, 1, 2, 2, 3]
    assert maximum([1, 1, 2, 2, 3], 0) == []
