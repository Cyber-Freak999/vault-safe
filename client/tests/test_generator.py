from __future__ import annotations

import string

import pytest

from vaultsafe_client.generator import generate_password


def test_default_length_is_20():
    assert len(generate_password()) == 20


def test_custom_length():
    assert len(generate_password(12)) == 12


@pytest.mark.parametrize("length", [7, 129, 0, -1])
def test_out_of_range_rejected(length: int):
    with pytest.raises(ValueError):
        generate_password(length)


def test_contains_each_character_class():
    pw = generate_password(24)
    assert any(c in string.ascii_lowercase for c in pw)
    assert any(c in string.ascii_uppercase for c in pw)
    assert any(c in string.digits for c in pw)
    assert any(c in string.punctuation for c in pw)


def test_generated_values_differ():
    assert len({generate_password() for _ in range(100)}) > 1
