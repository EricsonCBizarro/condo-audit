"""Every rule the engine runs, in report order."""

from __future__ import annotations

from condo_audit.audit.financial import (
    BalanceChainBreak,
    BudgetOverrun,
    DuplicatePayment,
    ForeignDocument,
    MissingReceipt,
    OpeningBalanceMismatch,
    ReceiptAmountMismatch,
)
from condo_audit.audit.governance import AgendaItemNotDeliberated, PenaltyLadderViolation, UnapprovedExpense
from condo_audit.audit.model import Rule

ALL_RULES: tuple[Rule, ...] = (
    BalanceChainBreak(),
    OpeningBalanceMismatch(),
    MissingReceipt(),
    ReceiptAmountMismatch(),
    DuplicatePayment(),
    BudgetOverrun(),
    UnapprovedExpense(),
    ForeignDocument(),
    PenaltyLadderViolation(),
    AgendaItemNotDeliberated(),
)

# Rules can emit findings under a secondary code (data-quality variants).
RULE_CODES: dict[str, tuple[str, ...]] = {"BALANCE_CHAIN_BREAK": ("BALANCE_CHAIN_BREAK", "LOW_CONFIDENCE_EXTRACTION")}


def select(codes: list[str] | None) -> tuple[Rule, ...]:
    if not codes:
        return ALL_RULES
    wanted = set(codes)
    return tuple(rule for rule in ALL_RULES if rule.code in wanted)
