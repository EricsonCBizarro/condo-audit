"""Brazilian money amounts in OCR'd text → Decimal (never float)."""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

# 1.234,56 | -1.234,56 | 234,56 | - 1 234,56 (OCR spacing). The decimal
# separator is always a comma followed by exactly two digits.
MONEY_RE = re.compile(r"(?<![\d.,/])(-\s?)?(\d{1,3}(?:[.\s]\d{3})+|\d+),(\d{2})(?![\d/])")


def parse_brl(value: str) -> Decimal | None:
    match = MONEY_RE.search(value)
    return _to_decimal(match) if match else None


def find_amounts(value: str) -> list[tuple[Decimal, int, int]]:
    """Every amount in the text with its (start, end) span, left to right."""
    found = []
    for match in MONEY_RE.finditer(value):
        amount = _to_decimal(match)
        if amount is not None:
            found.append((amount, match.start(), match.end()))
    return found


def _to_decimal(match: re.Match[str]) -> Decimal | None:
    sign, integer, cents = match.groups()
    digits = re.sub(r"[.\s]", "", integer)
    try:
        amount = Decimal(f"{digits}.{cents}")
    except InvalidOperation:  # pragma: no cover - regex guarantees digits
        return None
    return -amount if sign else amount
