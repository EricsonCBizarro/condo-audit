"""Fake CNPJ numbers that can never belong to a real company.

A CNPJ has two check digits computed from the first twelve. The generator
always writes *wrong* check digits, so a generated number fails validation
by construction (asserted by tests)."""

from __future__ import annotations

import random

_W1 = (5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)
_W2 = (6, *_W1)


def _check_digit(digits: list[int], weights: tuple[int, ...]) -> int:
    rest = sum(d * w for d, w in zip(digits, weights, strict=True)) % 11
    return 0 if rest < 2 else 11 - rest


def is_valid_cnpj(value: str) -> bool:
    digits = [int(c) for c in value if c.isdigit()]
    if len(digits) != 14 or len(set(digits)) == 1:
        return False
    first = _check_digit(digits[:12], _W1)
    second = _check_digit([*digits[:12], first], _W2)
    return digits[12:] == [first, second]


def fake_cnpj(rng: random.Random) -> str:
    """Formatted CNPJ (00.000.000/0001-00) whose check digits are invalid."""
    base = [rng.randint(0, 9) for _ in range(8)] + [0, 0, 0, 1]
    first = _check_digit(base, _W1)
    second = _check_digit([*base, first], _W2)
    wrong_second = (second + 1 + rng.randint(0, 7)) % 10
    d = [*base, first, wrong_second]
    s = "".join(map(str, d))
    return f"{s[:2]}.{s[2:5]}.{s[5:8]}/{s[8:12]}-{s[12:]}"
