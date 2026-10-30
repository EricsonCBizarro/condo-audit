from __future__ import annotations

from datetime import date

from condo_audit.audit.governance import AgendaItemNotDeliberated, PenaltyLadderViolation, UnapprovedExpense
from condo_audit.audit.model import AgendaItem, BudgetItem, Decision, Parameter, Penalty
from tests.audit.builders import D, context, entry, statement

LIMIT = Parameter(50, "spending_limit", {"amount": "5000.00"}, "Art. 18 ... R$ 5.000,00", 1)


def _ctx_with_payments(*payments: tuple[str, str, date]):  # type: ignore[no-untyped-def]
    ctx = context()
    ctx.parameters["spending_limit"] = LIMIT
    ctx.budget = [BudgetItem(51, 2025, "limpeza", D("4380.00"), 1)]
    doc = statement(ctx, date(2025, 5, 1))
    for description, amount, when in payments:
        entry(ctx, doc, description, amount, "1.00", when, category="obras")
    return ctx


def test_approved_expense_within_the_approved_amount_passes() -> None:
    ctx = _ctx_with_payments(
        ("PAGTO PINTURA FACHADA PARC 1/2 - TINTAS E REFORMAS", "-24000.00", date(2025, 5, 16)),
        ("PAGTO PINTURA FACHADA PARC 2/2 - TINTAS E REFORMAS", "-24000.00", date(2025, 6, 16)),
    )
    ctx.decisions = [Decision(60, date(2025, 3, 20), 3, "Pintura da fachada. aprovada", True, D("48000.00"), 1)]
    assert UnapprovedExpense().evaluate(ctx) == []


def test_payments_beyond_the_approved_amount_are_flagged() -> None:
    ctx = _ctx_with_payments(
        ("PAGTO PINTURA FACHADA PARC 1/2", "-30000.00", date(2025, 5, 16)),
        ("PAGTO PINTURA FACHADA PARC 2/2", "-30000.00", date(2025, 6, 16)),
    )
    ctx.decisions = [Decision(60, date(2025, 3, 20), 3, "Pintura da fachada. aprovada", True, D("48000.00"), 1)]
    [finding] = UnapprovedExpense().evaluate(ctx)
    assert "exceeds the amount approved" in finding.title


def test_rejected_by_the_assembly_and_paid_anyway() -> None:
    ctx = _ctx_with_payments(("PAGTO TROCA PORTAO ELETRONICO - SERRALHERIA", "-9700.00", date(2025, 10, 9)))
    ctx.decisions = [Decision(61, date(2025, 8, 14), 1, "Troca do portão eletrônico. não aprovada", False, None, 1)]
    [finding] = UnapprovedExpense().evaluate(ctx)
    assert "NOT approved" in finding.title
    assert {e.label for e in finding.evidence} == {"statement line", "convention", "meeting minutes"}


def test_approval_after_the_payment_does_not_count() -> None:
    ctx = _ctx_with_payments(("PAGTO TROCA PORTAO ELETRONICO", "-9700.00", date(2025, 7, 1)))
    ctx.decisions = [Decision(61, date(2025, 8, 14), 1, "Troca do portão eletrônico. aprovada", True, None, 1)]
    assert len(UnapprovedExpense().evaluate(ctx)) == 1


def test_budgeted_categories_and_amounts_below_the_limit_are_ordinary() -> None:
    ctx = _ctx_with_payments(("PAGTO REPARO", "-4999.99", date(2025, 5, 2)))
    entry(ctx, next(iter(ctx.documents)), "PAGTO LIMPEZA", "-6000.00", "1.00", date(2025, 5, 3), category="limpeza")
    assert UnapprovedExpense().evaluate(ctx) == []


def test_agenda_items_must_be_deliberated() -> None:
    ctx = context()
    meeting = date(2025, 8, 14)
    ctx.agenda = [
        AgendaItem(70, meeting, 1, "Troca do portão eletrônico", 1),
        AgendaItem(70, meeting, 2, "Regras de uso do salão de festas", 1),
        AgendaItem(70, meeting, 3, "Assuntos gerais", 1),
    ]
    ctx.decisions = [Decision(71, meeting, 1, "Troca do portão eletrônico. não aprovada", False, None, 1)]

    [finding] = AgendaItemNotDeliberated().evaluate(ctx)
    assert finding.subject == "70:2"
    assert finding.period == "2025-08"


def test_penalty_ladder_requires_a_warning_first_per_unit_and_infraction() -> None:
    ctx = context()
    ctx.parameters["penalty_ladder"] = Parameter(80, "penalty_ladder", {"steps": ["warning", "fine"]}, "8.1 ...", 1)
    ctx.penalties = [
        Penalty(90, "A-21", "Ruído após as 22h", "warning", None, date(2025, 2, 10), 1),
        Penalty(91, "A-21", "Ruído após as 22h", "fine", D("475.00"), date(2025, 6, 3), 1),
        Penalty(92, "B-12", "Animal solto", "fine", D("475.00"), date(2025, 4, 15), 1),
        Penalty(93, "A-21", "Uso da garagem", "warning", None, date(2025, 7, 1), 1),
    ]
    [finding] = PenaltyLadderViolation().evaluate(ctx)
    assert finding.subject == "92"
