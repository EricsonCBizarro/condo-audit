from __future__ import annotations

import random

from hypothesis import given
from hypothesis import strategies as st

from condo_audit.synth.taxid import _W1, _W2, _check_digit, fake_cnpj, is_valid_cnpj


def _valid_from(base: list[int]) -> str:
    """Build a checksum-valid number at runtime: the repository must not
    contain any literal that could be a real company's registration."""
    first = _check_digit(base, _W1)
    second = _check_digit([*base, first], _W2)
    return "".join(map(str, [*base, first, second]))


@given(st.lists(st.integers(min_value=0, max_value=9), min_size=12, max_size=12))
def test_validator_accepts_numbers_with_correct_check_digits(base: list[int]) -> None:
    if len(set(base)) > 1:  # all-equal digits are rejected by definition
        assert is_valid_cnpj(_valid_from(base))


def test_validator_rejects_repeated_digits_and_wrong_lengths() -> None:
    assert not is_valid_cnpj("11.111.111/1111-11")
    assert not is_valid_cnpj("123")


@given(st.integers(min_value=0, max_value=2**32))
def test_fake_cnpjs_are_never_valid(seed: int) -> None:
    value = fake_cnpj(random.Random(seed))
    assert len(value) == 18
    assert not is_valid_cnpj(value)
