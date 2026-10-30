from __future__ import annotations

from datetime import date

from condo_audit.audit.financial import (
    BalanceChainBreak,
    BudgetOverrun,
    DuplicatePayment,
    ForeignDocument,
    MissingReceipt,
    OpeningBalanceMismatch,
    ReceiptAmountMismatch,
)
from condo_audit.audit.model import BudgetItem, Category
from tests.audit.builders import D, context, entry, link, receipt, statement

MARCH = date(2025, 3, 1)


def test_balance_chain_break_reports_the_missing_amount() -> None:
    ctx = context()
    doc = statement(ctx, MARCH)
    entry(ctx, doc, "SALDO ANTERIOR", None, "1000.00", kind="opening_balance")
    entry(ctx, doc, "PAGTO AGUA", "-100.00", "700.00", date(2025, 3, 10), reconciliation="inconsistent")

    [finding] = BalanceChainBreak().evaluate(ctx)

    assert finding.rule_code == "BALANCE_CHAIN_BREAK"
    assert finding.amount == D("200.00")
    assert finding.period == "2025-03"


def test_low_confidence_breaks_become_review_items_not_accusations() -> None:
    ctx = context()
    doc = statement(ctx, MARCH)
    entry(ctx, doc, "SALDO ANTERIOR", None, "1000.00", kind="opening_balance")
    entry(ctx, doc, "PAGTO AGUA", "-100.00", "700.00", reconciliation="inconsistent", confidence=0.55)

    [finding] = BalanceChainBreak().evaluate(ctx)

    assert finding.rule_code == "LOW_CONFIDENCE_EXTRACTION"
    assert finding.category is Category.DATA_QUALITY


def test_opening_balance_must_match_previous_closing() -> None:
    ctx = context()
    feb, mar = statement(ctx, date(2025, 2, 1)), statement(ctx, MARCH)
    entry(ctx, feb, "SALDO FINAL", None, "5000.00", kind="closing_balance")
    entry(ctx, mar, "SALDO ANTERIOR", None, "4000.00", kind="opening_balance")

    [finding] = OpeningBalanceMismatch().evaluate(ctx)
    assert (finding.amount, finding.period) == (D("1000.00"), "2025-03")


def test_opening_balance_is_not_compared_across_a_missing_month() -> None:
    ctx = context()
    jan, mar = statement(ctx, date(2025, 1, 1)), statement(ctx, MARCH)
    entry(ctx, jan, "SALDO FINAL", None, "5000.00", kind="closing_balance")
    entry(ctx, mar, "SALDO ANTERIOR", None, "4000.00", kind="opening_balance")
    assert OpeningBalanceMismatch().evaluate(ctx) == []


def test_missing_receipt_respects_threshold_and_exempt_categories() -> None:
    ctx = context(receipt_threshold="500.00")
    doc = statement(ctx, MARCH)
    big = entry(ctx, doc, "PAGTO REPAROS", "-2800.00", "1.00", date(2025, 3, 3))
    entry(ctx, doc, "PAGTO CAFE", "-80.00", "1.00", date(2025, 3, 4))
    entry(ctx, doc, "TARIFA PACOTE", "-900.00", "1.00", date(2025, 3, 5), category="tarifas_bancarias")
    linked = entry(ctx, doc, "PAGTO LIMPEZA", "-900.00", "1.00", date(2025, 3, 6))
    link(ctx, linked, receipt(ctx, doc, "Limpa", "900.00", date(2025, 3, 6)))

    findings = MissingReceipt().evaluate(ctx)
    assert [f.subject for f in findings] == [str(big.id)]


def test_rejected_link_counts_as_no_receipt() -> None:
    ctx = context()
    doc = statement(ctx, MARCH)
    e = entry(ctx, doc, "PAGTO LIMPEZA", "-900.00", "1.00", date(2025, 3, 6))
    link(ctx, e, receipt(ctx, doc, "Limpa", "900.00", date(2025, 3, 6)), status="rejected")
    assert len(MissingReceipt().evaluate(ctx)) == 1


def test_receipt_amount_mismatch() -> None:
    ctx = context()
    doc = statement(ctx, MARCH)
    e = entry(ctx, doc, "PAGTO LIMPEZA", "-4380.00", "1.00", date(2025, 3, 15))
    link(ctx, e, receipt(ctx, doc, "Limpa Bem", "3840.00", date(2025, 3, 15)))

    [finding] = ReceiptAmountMismatch().evaluate(ctx)
    assert finding.amount == D("540.00")
    assert len(finding.evidence) == 2


def test_duplicate_payment_within_window_only() -> None:
    ctx = context(duplicate_window_days=10)
    doc = statement(ctx, MARCH)
    entry(ctx, doc, "PAGTO MANUTENCAO ELEVADOR", "-1200.00", "1.00", date(2025, 3, 7))
    entry(ctx, doc, "PAGTO MANUTENCAO ELEVADOR", "-1200.00", "1.00", date(2025, 3, 10))
    entry(ctx, doc, "PAGTO MANUTENCAO ELEVADOR", "-1200.00", "1.00", date(2025, 4, 7))  # next month: fine

    [finding] = DuplicatePayment().evaluate(ctx)
    assert finding.period == "2025-03"
    assert finding.title == "R$ 1.200,00 paid twice in 3 days"


def test_budget_overrun_uses_months_covered_and_tolerance() -> None:
    ctx = context(budget_tolerance="0.10")
    for month in (1, 2):
        doc = statement(ctx, date(2025, month, 1))
        entry(ctx, doc, "PAGTO JARDINAGEM", "-950.00", "1.00", date(2025, month, 20), category="jardinagem")
        entry(ctx, doc, "PAGTO ENERGIA", "-640.00", "1.00", date(2025, month, 8), category="energia")
    ctx.budget = [
        BudgetItem(99, 2025, "jardinagem", D("600.00"), 1),
        BudgetItem(99, 2025, "energia", D("600.00"), 1),  # 6.7% over: inside tolerance
    ]

    [finding] = BudgetOverrun().evaluate(ctx)
    assert finding.subject == "2025:jardinagem"
    assert finding.amount == D("700.00")


def test_foreign_document_by_name_or_tax_id_but_tolerates_ocr_noise() -> None:
    ctx = context()
    doc = statement(ctx, MARCH)
    when = date(2025, 3, 1)
    receipt(ctx, doc, "Águas", "10.00", when)  # ours
    receipt(ctx, doc, "Águas", "10.00", when, tax_id="12.345.678/0001-08")  # one digit misread
    other = receipt(
        ctx, doc, "Águas", "1870.40", when, payer="Condomínio Edifício Solar das Palmeiras", tax_id="98.765.432/0001-11"
    )

    [finding] = ForeignDocument().evaluate(ctx)
    assert finding.subject == str(other.id)
    assert finding.amount == D("1870.40")
