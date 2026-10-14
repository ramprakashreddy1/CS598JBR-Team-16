import pytest
from HumanEval_126 import *

import pytest
from HumanEval_126 import *

@pytest.mark.parametrize("lst, expected", [
    ([], True),
    ([1], True),
    ([1, 2], True),
    ([2, 1], False),
    ([1, 2, 3], True),
    ([3, 2, 1], False),
    ([1, 2, 2], True),
    ([2, 2, 1], False),
    ([1, 2, 3, 4], True),
    ([4, 3, 2, 1], False),
    ([1, 2, 2, 3], True),
    ([3, 2, 2, 1], False),
    ([1, 2, 3, 4, 5], True),
    ([5, 4, 3, 2, 1], False),
    ([1, 2, 3, 4, 5, 6], True),
    ([6, 5, 4, 3, 2, 1], False),
    ([1, 2, 3, 4, 5, 6, 7], True),
    ([7, 6, 5, 4, 3, 2, 1], False),
    ([1, 2, 2, 3, 4], True),
    ([4, 3, 2, 2, 1], False),
    ([1, 2, 2, 2, 3, 4], True),
    ([4, 3, 2, 2, 1], False),
    ([1, 2, 3, 4, 5, 6, 7, 8], True),
    ([8, 7, 6, 5, 4, 3, 2, 1], False),
    ([1, 2, 3, 4, 5, 6, 7, 8, 9], True),
    ([9, 8, 7, 6, 5, 4, 3, 2, 1], False),
    ([1, 1, 2, 3, 4, 5], True),
    ([5, 5, 4, 3, 2, 1], False),
    ([1, 1, 1, 2, 3, 4], True),
    ([4, 4, 3, 2, 2, 1], False),
    ([1, 1, 1, 1, 2, 3, 4], True),
    ([4, 4, 4, 3, 2, 2, 1], False),
    ([1, 2, 3, 3, 4, 5], True),
    ([5, 4, 3, 3, 2, 1], False),
    ([1, 2, 3, 3, 3, 4], True),
    ([4, 3, 3, 2, 2, 1], False),
    ([1, 2, 2, 2, 3, 4], True),
    ([4, 3, 3, 2, 2, 1], False),
    ([1, 2, 2, 2, 2, 3, 4], True),
    ([4, 3, 3, 3, 2, 2, 1], False),
    ([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], True),
    ([10, 9, 8, 7, 6, 5, 4, 3, 2, 1], False),
    ([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11], True),
    ([11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1], False),
])
def test_is_sorted(lst, expected):
    assert is_sorted(lst) == expected
