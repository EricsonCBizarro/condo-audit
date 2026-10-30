from __future__ import annotations

from decimal import Decimal

import pytest

from condo_audit.formatting import brl


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (Decimal("0"), "0,00"),
        (Decimal("5"), "5,00"),
        (Decimal("1234.5"), "1.234,50"),
        (Decimal("-48000"), "-48.000,00"),
        (Decimal("1234567.891"), "1.234.567,89"),
    ],
)
def test_brl(value: Decimal, expected: str) -> None:
    assert brl(value) == expected
