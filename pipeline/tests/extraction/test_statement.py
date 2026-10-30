from __future__ import annotations

from decimal import Decimal

from condo_audit.extraction.statement import Reconciliation, RowKind, parse_rows
from tests.helpers import page_from_lines

STATEMENT = [
    "BALANCETE MENSAL",
    "Data Histórico Valor (R$) Saldo (R$)",
    "28/02/2025 SALDO ANTERIOR 1.000,00",
    "05/03/2025 TED RECEBIDA - TAXAS 500,00 1.500,00",
    "06/03/2025 | PAGTO LIMPEZA - LIMPA BEM -200,00 1.300,00",
    "10/03/2025 PAGTO AGUA -100,00 1.000,00",
    "12/03/2025 PAGTO ENERGIA 50,00 950,00",
    "31/03/2025 SALDO FINAL 950,00",
]


def test_rows_are_parsed_and_reconciled() -> None:
    rows = parse_rows([page_from_lines(STATEMENT)])

    assert [r.kind for r in rows] == [RowKind.OPENING, *[RowKind.TRANSACTION] * 4, RowKind.CLOSING]
    assert rows[2].description == "PAGTO LIMPEZA - LIMPA BEM"
    assert rows[2].amount == Decimal("-200.00")
    assert [r.reconciliation for r in rows] == [
        Reconciliation.OK,
        Reconciliation.OK,
        Reconciliation.OK,
        Reconciliation.INCONSISTENT,  # 1.300 - 100 = 1.200, printed 1.000: 200 vanished
        Reconciliation.OK_INFERRED_SIGN,  # OCR lost the minus sign of a debit
        Reconciliation.OK,
    ]


def test_inferred_sign_is_applied_to_the_amount() -> None:
    rows = parse_rows([page_from_lines(STATEMENT)])
    assert rows[4].amount == Decimal("-50.00")


def test_a_break_does_not_cascade_to_the_following_rows() -> None:
    rows = parse_rows([page_from_lines(STATEMENT)])
    assert sum(r.reconciliation is Reconciliation.INCONSISTENT for r in rows) == 1


def test_rows_spanning_pages_keep_the_running_balance() -> None:
    first = page_from_lines(STATEMENT[:4], number=1)
    second = page_from_lines(["06/03/2025 PAGTO X -500,00 1.000,00", "31/03/2025 SALDO FINAL 1.000,00"], number=2)
    rows = parse_rows([first, second])
    assert rows[-2].page == 2
    assert all(r.reconciliation is Reconciliation.OK for r in rows)
