from __future__ import annotations

from decimal import Decimal

from condo_audit.audit.model import FindingDraft, Severity
from condo_audit.audit.registry import ALL_RULES, select
from condo_audit.evaluation.metrics import Detected, Expected, evaluate


def test_fingerprint_depends_on_rule_and_subject_only() -> None:
    a = FindingDraft("X", "42", "title", "text", Severity.LOW, amount=Decimal(1))
    b = FindingDraft("X", "42", "other title", "other text", Severity.HIGH, amount=Decimal(2))
    c = FindingDraft("Y", "42", "title", "text", Severity.LOW)
    assert a.fingerprint == b.fingerprint != c.fingerprint


def test_rule_codes_are_unique_and_selectable() -> None:
    codes = [r.code for r in ALL_RULES]
    assert len(codes) == len(set(codes)) == 10
    assert [r.code for r in select(["DUPLICATE_PAYMENT"])] == ["DUPLICATE_PAYMENT"]
    assert select(None) == ALL_RULES


def test_metrics_match_by_rule_period_and_amount() -> None:
    expected = [
        Expected("c", "DUPLICATE_PAYMENT", "2025-07", Decimal("1200.00")),
        Expected("c", "MISSING_RECEIPT", "2025-04", Decimal("2800.00")),
    ]
    detected = [
        Detected("c", "DUPLICATE_PAYMENT", "2025-07", Decimal("1200.00")),
        Detected("c", "MISSING_RECEIPT", "2025-04", Decimal("999.00")),  # wrong amount
        Detected("other", "DUPLICATE_PAYMENT", "2025-07", Decimal("1200.00")),  # control group
    ]
    report = evaluate(expected, detected)
    total = report.total
    assert (total.true_positives, total.false_positives, total.false_negatives) == (1, 2, 1)
    assert report.by_rule["DUPLICATE_PAYMENT"].precision == 0.5
    assert report.by_rule["MISSING_RECEIPT"].recall == 0.0
