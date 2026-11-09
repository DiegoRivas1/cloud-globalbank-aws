import pytest

from server import parse_start


def test_valido():
    assert parse_start({"mode": "work", "rps": 50, "duration": 30, "ms": 80}, 500, 300) == (
        "work", 50.0, 30.0, 80)


@pytest.mark.parametrize("data", [
    None, [], {"rps": 0, "duration": 10}, {"rps": 501, "duration": 10},
    {"rps": 10, "duration": 0}, {"rps": 10, "duration": 301},
    {"rps": "abc", "duration": 10}, {"mode": "hack", "rps": 10, "duration": 10},
    {"rps": 10, "duration": 10, "ms": 5000}, {"duration": 10},
])
def test_invalido(data):
    with pytest.raises(ValueError):
        parse_start(data, 500, 300)
