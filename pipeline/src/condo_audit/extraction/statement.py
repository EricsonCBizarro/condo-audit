"""Bank statement rows and balance reconciliation.

Each row is checked against the running balance:

    previous balance + amount == printed balance   → ok
    previous balance - amount == printed balance   → ok_inferred_sign (OCR lost the minus)
    otherwise                                      → inconsistent

After an inconsistent row the chain continues from the printed balance, so
one bad row produces one break, not a cascade.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date
from decimal import Decimal
from enum import StrEnum

from condo_audit.documents.layout import PageLayout
from condo_audit.extraction.money import find_amounts
from condo_audit.extraction.text import DATE_RE, clean_tokens, normalize, parse_date

TOLERANCE = Decimal("0.005")


class RowKind(StrEnum):
    OPENING = "opening_balance"
    TRANSACTION = "transaction"
    CLOSING = "closing_balance"


class Reconciliation(StrEnum):
    OK = "ok"
    OK_INFERRED_SIGN = "ok_inferred_sign"
    INCONSISTENT = "inconsistent"
    NO_REFERENCE = "no_reference"
    UNPARSED = "unparsed"


@dataclass(frozen=True, slots=True)
class StatementRow:
    page: int
    line: int
    kind: RowKind
    entry_date: date | None
    description: str
    amount: Decimal | None
    balance: Decimal | None
    confidence: float
    raw_text: str
    reconciliation: Reconciliation = Reconciliation.NO_REFERENCE
    expected_balance: Decimal | None = None


def parse_rows(pages: list[PageLayout]) -> list[StatementRow]:
    rows: list[StatementRow] = []
    for page in pages:
        for index, line in enumerate(page.lines, start=1):
            raw = clean_tokens(line.text)
            match = DATE_RE.match(raw)
            if not match:
                continue
            rest = raw[match.end() :].strip()
            amounts = find_amounts(rest)
            first_amount_at = amounts[0][1] if amounts else len(rest)
            description = rest[:first_amount_at].strip(" -")
            label = normalize(description)
            values = [a for a, _, _ in amounts]

            if "SALDO" in label and "ANTER" in label:
                kind, amount, balance = RowKind.OPENING, None, values[-1] if values else None
            elif "SALDO" in label and "FINAL" in label:
                kind, amount, balance = RowKind.CLOSING, None, values[-1] if values else None
            else:
                kind = RowKind.TRANSACTION
                amount = values[0] if len(values) >= 2 else None
                balance = values[-1] if len(values) >= 2 else None

            rows.append(
                StatementRow(
                    page=page.number,
                    line=index,
                    kind=kind,
                    entry_date=parse_date(raw),
                    description=description,
                    amount=amount,
                    balance=balance,
                    confidence=line.confidence,
                    raw_text=raw,
                )
            )
    return reconcile(rows)


def reconcile(rows: list[StatementRow]) -> list[StatementRow]:
    out: list[StatementRow] = []
    running: Decimal | None = None
    for row in rows:
        if row.kind is RowKind.OPENING:
            running = row.balance
            out.append(
                replace(row, reconciliation=Reconciliation.OK if running is not None else Reconciliation.UNPARSED)
            )
            continue
        if row.kind is RowKind.CLOSING:
            status = _compare(running, row.balance)
            out.append(replace(row, reconciliation=status, expected_balance=running))
            continue
        if row.amount is None or row.balance is None:
            out.append(replace(row, reconciliation=Reconciliation.UNPARSED))
            continue
        if running is None:
            out.append(replace(row, reconciliation=Reconciliation.NO_REFERENCE))
            running = row.balance
            continue
        expected = running + row.amount
        if abs(expected - row.balance) <= TOLERANCE:
            out.append(replace(row, reconciliation=Reconciliation.OK, expected_balance=expected))
        elif abs(running - row.amount - row.balance) <= TOLERANCE:
            out.append(
                replace(
                    row,
                    amount=-row.amount,
                    reconciliation=Reconciliation.OK_INFERRED_SIGN,
                    expected_balance=running - row.amount,
                )
            )
        else:
            out.append(replace(row, reconciliation=Reconciliation.INCONSISTENT, expected_balance=expected))
        running = row.balance
    return out


def _compare(expected: Decimal | None, printed: Decimal | None) -> Reconciliation:
    if expected is None or printed is None:
        return Reconciliation.NO_REFERENCE
    return Reconciliation.OK if abs(expected - printed) <= TOLERANCE else Reconciliation.INCONSISTENT
