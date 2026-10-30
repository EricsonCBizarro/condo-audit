"""Brazilian number and date formatting (documents and finding texts)."""

from __future__ import annotations

from datetime import date
from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")

MONTHS_PT = [
    "janeiro",
    "fevereiro",
    "março",
    "abril",
    "maio",
    "junho",
    "julho",
    "agosto",
    "setembro",
    "outubro",
    "novembro",
    "dezembro",
]


def money(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def brl(value: Decimal, signed: bool = False) -> str:
    """1234.5 → '1.234,50' (and '-1.234,50' for negatives)."""
    q = money(value)
    sign = "-" if q < 0 else ("+" if signed and q > 0 else "")
    integer, _, cents = f"{abs(q):.2f}".partition(".")
    groups: list[str] = []
    while integer:
        groups.insert(0, integer[-3:])
        integer = integer[:-3]
    return f"{sign}{'.'.join(groups)},{cents}"


def d(value: date) -> str:
    return value.strftime("%d/%m/%Y")


def long_date(value: date) -> str:
    return f"{value.day} de {MONTHS_PT[value.month - 1]} de {value.year}"
