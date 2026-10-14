import pytest
from HumanEval_81 import *

import pytest
from HumanEval_81 import numerical_letter_grade

def test_numerical_letter_grade_empty():
    assert numerical_letter_grade([]) == []

def test_numerical_letter_grade_Aplus():
    assert numerical_letter_grade([4.0]) == ["A+"]

def test_numerical_letter_grade_A():
    assert numerical_letter_grade([4.0]) == ["A+"]

def test_numerical_letter_grade_Aminus():
    assert numerical_letter_grade([3.7]) == ["A"]

def test_numerical_letter_grade_Bplus():
    assert numerical_letter_grade([3.3]) == ["A-"]

def test_numerical_letter_grade_B():
    assert numerical_letter_grade([3.0]) == ["B+"]

def test_numerical_letter_grade_Bminus():
    assert numerical_letter_grade([2.7]) == ["B"]

def test_numerical_letter_grade_Cplus():
    assert numerical_letter_grade([2.3]) == ["B-"]

def test_numerical_letter_grade_C():
    assert numerical_letter_grade([2.0]) == ["C+"]

def test_numerical_letter_grade_Cminus():
    assert numerical_letter_grade([1.7]) == ["C"]

def test_numerical_letter_grade_Dplus():
    assert numerical_letter_grade([1.3]) == ["C-"]

def test_numerical_letter_grade_D():
    assert numerical_letter_grade([1.0]) == ["D+"]

def test_numerical_letter_grade_Dminus():
    assert numerical_letter_grade([0.7]) == ["D"]

def test_numerical_letter_grade_E():
    assert numerical_letter_grade([0.0]) == ["E"]

def test_numerical_letter_grade_multiple_grades():
    assert numerical_letter_grade([4.0, 3, 1.7, 2, 3.5]) == ['A+', 'B', 'C-', 'C', 'A-']


# ---- additional tests from coverage feedback ----
import pytest
from HumanEval_81 import *

import pytest
from HumanEval_81 import numerical_letter_grade

def test_numerical_letter_grade_Aplus_extra():
    assert numerical_letter_grade([4.0]) == ["A+"]

def test_numerical_letter_grade_A_extra():
    assert numerical_letter_grade([4.0, 3.8]) == ["A+", "A"]

def test_numerical_letter_grade_Aminus_extra():
    assert numerical_letter_grade([4.0, 3.4]) == ["A+", "A-"]

def test_numerical_letter_grade_Bplus_extra():
    assert numerical_letter_grade([4.0, 3.4, 3.1]) == ["A+", "A-", "B+"]

def test_numerical_letter_grade_B_extra():
    assert numerical_letter_grade([4.0, 3.8, 3.1, 2.8]) == ["A+", "A", "B+", "B"]

def test_numerical_letter_grade_Bminus_extra():
    assert numerical_letter_grade([4.0, 3.4, 3.1, 2.4]) == ["A+", "A-", "B+", "B-"]

def test_numerical_letter_grade_Cplus_extra():
    assert numerical_letter_grade([4.0, 3.4, 3.1, 2.4, 2.1]) == ["A+", "A-", "B+", "B-", "C+"]

def test_numerical_letter_grade_C_extra():
    assert numerical_letter_grade([4.0, 3.8, 3.1, 2.8, 2.1, 1.8]) == ["A+", "A", "B+", "B", "C+", "C"]

def test_numerical_letter_grade_Cminus_extra():
    assert numerical_letter_grade([4.0, 3.4, 3.1, 2.4, 2.1, 1.4]) == ["A+", "A-", "B+", "B-", "C+", "C-"]

def test_numerical_letter_grade_Dplus_extra():
    assert numerical_letter_grade([4.0, 3.4, 3.1, 2.4, 2.1, 1.4, 1.1]) == ["A+", "A-", "B+", "B-", "C+", "C-", "D+"]

def test_numerical_letter_grade_D_extra():
    assert numerical_letter_grade([4.0, 3.8, 3.1, 2.8, 2.1, 1.8, 1.1, 0.8]) == ["A+", "A", "B+", "B", "C+", "C", "D+", "D"]

def test_numerical_letter_grade_Dminus_extra():
    assert numerical_letter_grade([4.0, 3.4, 3.1, 2.4, 2.1, 1.4, 1.1, 0.4]) == ["A+", "A-", "B+", "B-", "C+", "C-", "D+", "D-"]

def test_numerical_letter_grade_E_extra():
    assert numerical_letter_grade([4.0, 3.4, 3.1, 2.4, 2.1, 1.4, 1.1, 0.4, 0.0]) == ["A+", "A-", "B+", "B-", "C+", "C-", "D+", "D-", "E"]
