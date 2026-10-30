from __future__ import annotations

from datetime import date
from decimal import Decimal

from condo_audit.linking import Debit, ReceiptRef, assign


def test_equal_amount_and_payee_wins() -> None:
    debits = [Debit(1, "PAGTO LIMPEZA - LIMPA BEM SERVICOS", Decimal("-4380.00"), date(2025, 5, 15))]
    receipts = [
        ReceiptRef(10, "Outra Empresa", Decimal("4380.00"), date(2025, 5, 2)),
        ReceiptRef(11, "Limpa Bem Serviços Ltda.", Decimal("4380.00"), date(2025, 5, 15)),
    ]
    assert assign(debits, receipts) == [(1, 11, Decimal("1.0"))]


def test_same_payee_and_date_with_a_different_amount_is_still_linked() -> None:
    debits = [Debit(1, "PAGTO LIMPEZA - LIMPA BEM SERVICOS", Decimal("-4380.00"), date(2025, 5, 15))]
    receipts = [ReceiptRef(11, "Limpa Bem Serviços Ltda.", Decimal("3840.00"), date(2025, 5, 15))]
    assert assign(debits, receipts) == [(1, 11, Decimal("0.4"))]


def test_each_receipt_supports_one_payment_only() -> None:
    debits = [
        Debit(1, "PAGTO ELEVADORES ASCENDE", Decimal("-1200.00"), date(2025, 7, 7)),
        Debit(2, "PAGTO ELEVADORES ASCENDE", Decimal("-1200.00"), date(2025, 7, 10)),
    ]
    receipts = [ReceiptRef(10, "Elevadores Ascende", Decimal("1200.00"), date(2025, 7, 7))]
    assert assign(debits, receipts) == [(1, 10, Decimal("1.0"))]


def test_rejected_pairs_are_never_suggested_again() -> None:
    debits = [Debit(1, "PAGTO ELEVADORES ASCENDE", Decimal("-1200.00"), date(2025, 7, 7))]
    receipts = [ReceiptRef(10, "Elevadores Ascende", Decimal("1200.00"), date(2025, 7, 7))]
    assert assign(debits, receipts, blocked={(1, 10)}) == []
