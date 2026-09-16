import pytest
from agents.A002_News_Intelligence.intelligence.predict import _direction_of

def test_direction_of_none():
    assert _direction_of(None, 0.5) == "unknown"
    assert _direction_of(None, 1.0) == "unknown"

def test_direction_of_flat():
    assert _direction_of(0.0, 0.5) == "flat"
    assert _direction_of(0.05, 0.5) == "flat"
    assert _direction_of(-0.05, 0.5) == "flat"
    assert _direction_of(0.099, 0.5) == "flat"
    assert _direction_of(-0.099, 0.5) == "flat"

def test_direction_of_up():
    assert _direction_of(0.1, 0.5) == "up"
    assert _direction_of(0.5, 0.5) == "up"
    assert _direction_of(1.5, 0.5) == "up"

def test_direction_of_down():
    assert _direction_of(-0.1, 0.5) == "down"
    assert _direction_of(-0.5, 0.5) == "down"
    assert _direction_of(-1.5, 0.5) == "down"
