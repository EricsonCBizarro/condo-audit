"""Precision/recall of findings against ground truth.

A finding matches an expected item when the rule code and the period are
equal and, when both carry an amount, the amounts agree to the cent. Each
expected item can be matched once. Only `irregularity` findings count:
data-quality items are review requests, not accusations.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class Expected:
    condominium: str
    rule_code: str
    period: str
    amount: Decimal | None
    note: str = ""


@dataclass(frozen=True, slots=True)
class Detected:
    condominium: str
    rule_code: str
    period: str | None
    amount: Decimal | None
    title: str = ""


@dataclass
class RuleScore:
    true_positives: int = 0
    false_positives: int = 0
    false_negatives: int = 0

    @property
    def precision(self) -> float:
        found = self.true_positives + self.false_positives
        return self.true_positives / found if found else 1.0

    @property
    def recall(self) -> float:
        expected = self.true_positives + self.false_negatives
        return self.true_positives / expected if expected else 1.0


@dataclass
class Report:
    by_rule: dict[str, RuleScore] = field(default_factory=lambda: defaultdict(RuleScore))
    missed: list[Expected] = field(default_factory=list)
    unexpected: list[Detected] = field(default_factory=list)

    @property
    def total(self) -> RuleScore:
        t = RuleScore()
        for s in self.by_rule.values():
            t.true_positives += s.true_positives
            t.false_positives += s.false_positives
            t.false_negatives += s.false_negatives
        return t


def _matches(e: Expected, f: Detected) -> bool:
    if (e.condominium, e.rule_code, e.period) != (f.condominium, f.rule_code, f.period):
        return False
    return e.amount is None or f.amount is None or abs(e.amount - f.amount) <= Decimal("0.01")


def evaluate(expected: list[Expected], detected: list[Detected]) -> Report:
    report = Report()
    remaining = list(expected)
    for f in detected:
        hit = next((e for e in remaining if _matches(e, f)), None)
        if hit is None:
            report.by_rule[f.rule_code].false_positives += 1
            report.unexpected.append(f)
        else:
            remaining.remove(hit)
            report.by_rule[f.rule_code].true_positives += 1
    for e in remaining:
        report.by_rule[e.rule_code].false_negatives += 1
        report.missed.append(e)
    return report
