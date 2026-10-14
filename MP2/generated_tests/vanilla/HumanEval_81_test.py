import pytest
from HumanEval_81 import *

import pytest
from HumanEval_81 import *

def test_numerical_letter_grade():
    assert numerical_letter_grade([4.0]) == ["A+"]
    assert numerical_letter_grade([4.1]) == ["A"]
    assert numerical_letter_grade([3.8]) == ["A-"]
    assert numerical_letter_grade([3.4]) == ["B+"]
    assert numerical_letter_grade([3.2]) == ["B"]
    assert numerical_letter_grade([2.8]) == ["B-"]
    assert numerical_letter_grade([2.4]) == ["C+"]
    assert numerical_letter_grade([2.2]) == ["C"]
    assert numerical_letter_grade([1.8]) == ["C-"]
    assert numerical_letter_grade([1.4]) == ["D+"]
    assert numerical_letter_grade([1.2]) == ["D"]
    assert numerical_letter_grade([0.8]) == ["D-"]
    assert numerical_letter_grade([0.0]) == ["E"]
    assert numerical_letter_grade([0.6]) == ["E"]
    assert numerical_letter_grade([4.2]) == ["E"]
