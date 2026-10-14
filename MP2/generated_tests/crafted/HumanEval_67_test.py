import pytest
from HumanEval_67 import *

import pytest
from HumanEval_67 import *

def test_fruit_distribution():
    # Test with empty string
    assert fruit_distribution("", 0) == 0

    # Test with single element
    assert fruit_distribution("0 apples and 0 oranges", 0) == 0

    # Test with zero
    assert fruit_distribution("0 apples and 0 oranges", 0) == 0

    # Test with negative numbers
    with pytest.raises(ValueError):
        fruit_distribution("-1 apples and -1 oranges", -2)

    # Test with boundary values
