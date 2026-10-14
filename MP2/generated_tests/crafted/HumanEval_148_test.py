import pytest
from HumanEval_148 import *

import pytest
from HumanEval_148 import bf

def test_bf():
    # Test with valid planets
    assert bf("Jupiter", "Neptune") == ("Saturn", "Uranus")
    assert bf("Earth", "Mercury") == ("Venus")
    assert bf("Mercury", "Uranus") == ("Venus", "Earth", "Mars", "Jupiter", "Saturn")

    # Test with invalid planets
    assert bf("Earth", "Pluto") == ()
    assert bf("Pluto", "Earth") == ()
    assert bf("Earth", "Earth") == ()

    # Test with planets in reverse order
    assert bf("Neptune", "Jupiter") == ("Saturn", "Uranus")

    # Test with same planets
    assert bf("Mercury", "Mercury") == ()
    assert bf("Neptune", "Neptune") == ()

    # Test with planets at the same index
    assert bf("Venus", "Venus") == ()
    assert bf("Mars", "Mars") == ()

    # Test with planets at the end of the tuple
    assert bf("Saturn", "Neptune") == ()
    assert bf("Uranus", "Neptune") == ()

    # Test with planets at the beginning of the tuple
    assert bf("Mercury", "Jupiter") == ("Venus", "Earth", "Mars", "Jupiter")
    assert bf("Mercury", "Saturn") == ("Venus", "Earth", "Mars", "Jupiter", "Saturn")

    # Test with planets at the beginning and end of the tuple
    assert bf("Mercury", "Neptune") == ("Venus", "Earth", "Mars", "Jupiter", "Saturn", "Uranus")


# ---- additional tests from coverage feedback ----
import pytest
from HumanEval_148 import *

import pytest
from HumanEval_148 import bf

def test_bf_jupiter_neptune_extra():
    assert bf("Jupiter", "Neptune") == ("Saturn", "Uranus")

def test_bf_earth_mercury_extra():
    assert bf("Earth", "Mercury") == ("Venus",)

def test_bf_mercury_uranus_extra():
    assert bf("Mercury", "Uranus") == ("Venus", "Earth", "Mars", "Jupiter", "Saturn")

def test_bf_planet1_not_in_planet_names_extra():
    assert bf("Pluto", "Neptune") == ()

def test_bf_planet2_not_in_planet_names_extra():
    assert bf("Jupiter", "Pluto") == ()

def test_bf_planet1_equals_planet2_extra():
    assert bf("Jupiter", "Jupiter") == ()
