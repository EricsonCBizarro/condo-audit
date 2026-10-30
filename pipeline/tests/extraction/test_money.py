from __future__ import annotations

from decimal import Decimal

import pytest
from hypothesis import given
from hypothesis import strategies as st

from condo_audit.extraction.money import find_amounts, parse_brl
from condo_audit.formatting import brl


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Valor: R$ 1.234,56", Decimal("1234.56")),
        ("-3.337,92", Decimal("-3337.92")),
        ("- 950,00", Decimal("-950.00")),
        ("58,90", Decimal("58.90")),
        ("1 234,56", Decimal("1234.56")),  # OCR read the thousands dot as a space
        ("12.345.678,90", Decimal("12345678.90")),
        ("sem valor", None),
        ("05/10/2025", None),  # dates are not money
    ],
)
def test_parse_brl(text: str, expected: Decimal | None) -> None:
    assert parse_brl(text) == expected


def test_find_amounts_returns_every_value_with_its_position() -> None:
    text = "PAGTO AGUA - AGUAS DO VALE -3.309,48 19.945,06"
    amounts = find_amounts(text)
    assert [a for a, _, _ in amounts] == [Decimal("-3309.48"), Decimal("19945.06")]
    assert text[amounts[0][1] : amounts[0][2]] == "-3.309,48"


@given(st.decimals(min_value=Decimal("-99999999.99"), max_value=Decimal("99999999.99"), places=2))
def test_formatting_and_parsing_round_trip(value: Decimal) -> None:
    assert parse_brl(brl(value)) == value
