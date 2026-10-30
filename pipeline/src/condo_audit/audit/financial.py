"""Rules over the money: statements, receipts and budget."""

from __future__ import annotations

import itertools
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from condo_audit.audit.model import (
    AuditContext,
    Category,
    Entry,
    Evidence,
    FindingDraft,
    Receipt,
    Severity,
)
from condo_audit.extraction.text import significant_tokens
from condo_audit.formatting import brl, d

CENT = Decimal("0.005")
NO_RECEIPT_EXPECTED = {"tarifas_bancarias"}


def month(value: date | None) -> str | None:
    return f"{value:%Y-%m}" if value else None


def line_evidence(e: Entry, label: str = "statement line") -> Evidence:
    return Evidence(e.document_id, e.page, e.raw_text, label)


def receipt_evidence(r: Receipt, label: str = "receipt") -> Evidence:
    parts = [
        f"Favorecido: {r.payee}" if r.payee else None,
        f"Valor: R$ {brl(r.amount)}" if r.amount is not None else None,
        f"Data: {d(r.paid_on)}" if r.paid_on else None,
        f"Pagador: {r.payer_name}" if r.payer_name else None,
        f"CNPJ do pagador: {r.payer_tax_id}" if r.payer_tax_id else None,
    ]
    return Evidence(r.document_id, r.page, " | ".join(p for p in parts if p), label)


def _by_document(entries: list[Entry]) -> dict[int, list[Entry]]:
    grouped: dict[int, list[Entry]] = defaultdict(list)
    for e in entries:
        grouped[e.document_id].append(e)
    for rows in grouped.values():
        rows.sort(key=lambda e: (e.page, e.line))
    return grouped


def _debits(ctx: AuditContext) -> list[Entry]:
    return [e for e in ctx.entries if e.kind == "transaction" and e.amount is not None and e.amount < 0]


@dataclass(frozen=True)
class BalanceChainBreak:
    """Previous balance + entry must equal the printed balance.

    A break on a line read by OCR with low confidence is reported as a data
    quality item (someone should look at the page) instead of an irregularity:
    the tool must not accuse anyone because a digit was misread.
    """

    code: str = "BALANCE_CHAIN_BREAK"
    description: str = "Running balance printed on the statement does not add up."

    def evaluate(self, ctx: AuditContext) -> list[FindingDraft]:
        min_confidence = float(ctx.setting("ocr_min_confidence", 0.8))
        findings = []
        for rows in _by_document(ctx.entries).values():
            previous: Decimal | None = None
            for e in rows:
                if e.kind == "opening_balance":
                    previous = e.balance
                    continue
                if e.reconciliation == "inconsistent" and previous is not None and e.balance is not None:
                    expected = previous + (e.amount or Decimal(0)) if e.kind == "transaction" else previous
                    gap = abs(e.balance - expected)
                    findings.append(self._finding(e, expected, gap, min_confidence))
                if e.balance is not None:
                    previous = e.balance
        return findings

    def _finding(self, e: Entry, expected: Decimal, gap: Decimal, min_confidence: float) -> FindingDraft:
        subject = f"{e.document_id}:{e.page}:{e.line}"
        if e.confidence < min_confidence:
            return FindingDraft(
                rule_code="LOW_CONFIDENCE_EXTRACTION",
                subject=subject,
                title="Statement line needs manual review",
                explanation=(
                    f"The balance on this line does not add up (expected R$ {brl(expected)}, printed "
                    f"R$ {brl(e.balance or Decimal(0))}), but the line was read with low OCR confidence "
                    f"({e.confidence:.0%}). Check the original page before drawing conclusions."
                ),
                severity=Severity.LOW,
                category=Category.DATA_QUALITY,
                amount=gap,
                period=month(e.entry_date),
                evidence=(line_evidence(e),),
            )
        return FindingDraft(
            rule_code=self.code,
            subject=subject,
            title=f"R$ {brl(gap)} unaccounted for in the running balance",
            explanation=(
                f"After '{e.description}' the statement prints a balance of R$ {brl(e.balance or Decimal(0))}, "
                f"but the previous balance plus this entry gives R$ {brl(expected)}. "
                "Money entered or left the account without a corresponding entry."
            ),
            severity=Severity.HIGH,
            amount=gap,
            period=month(e.entry_date),
            evidence=(line_evidence(e),),
        )


@dataclass(frozen=True)
class OpeningBalanceMismatch:
    code: str = "OPENING_BALANCE_MISMATCH"
    description: str = "A month must open with the previous month's closing balance."

    def evaluate(self, ctx: AuditContext) -> list[FindingDraft]:
        statements = sorted(
            (doc for doc in ctx.documents.values() if doc.type == "financial_statement" and doc.reference_period),
            key=lambda doc: doc.reference_period or date.min,
        )
        rows = _by_document(ctx.entries)
        findings = []
        for prev, cur in itertools.pairwise(statements):
            if prev.reference_period is None or cur.reference_period is None:
                continue
            gap_months = (cur.reference_period.year - prev.reference_period.year) * 12 + (
                cur.reference_period.month - prev.reference_period.month
            )
            closing = next((e for e in reversed(rows.get(prev.id, [])) if e.kind == "closing_balance"), None)
            opening = next((e for e in rows.get(cur.id, []) if e.kind == "opening_balance"), None)
            if gap_months != 1 or not closing or not opening or closing.balance is None or opening.balance is None:
                continue
            diff = opening.balance - closing.balance
            if abs(diff) <= CENT:
                continue
            findings.append(
                FindingDraft(
                    rule_code=self.code,
                    subject=f"{prev.id}->{cur.id}",
                    title=f"Opening balance differs from the previous closing by R$ {brl(abs(diff))}",
                    explanation=(
                        f"{prev.title} closes at R$ {brl(closing.balance)}, but {cur.title} opens at "
                        f"R$ {brl(opening.balance)}. The difference was not moved by any statement entry."
                    ),
                    severity=Severity.HIGH,
                    amount=abs(diff),
                    period=month(cur.reference_period),
                    evidence=(line_evidence(closing, "previous closing"), line_evidence(opening, "opening")),
                )
            )
        return findings


@dataclass(frozen=True)
class MissingReceipt:
    code: str = "MISSING_RECEIPT"
    description: str = "Payments above the threshold must have a receipt."

    def evaluate(self, ctx: AuditContext) -> list[FindingDraft]:
        threshold = Decimal(str(ctx.setting("receipt_threshold", "500.00")))
        findings = []
        for e in _debits(ctx):
            if e.amount is None or abs(e.amount) < threshold or e.category in NO_RECEIPT_EXPECTED or ctx.link_for(e.id):
                continue
            findings.append(
                FindingDraft(
                    rule_code=self.code,
                    subject=str(e.id),
                    title=f"No receipt for a R$ {brl(abs(e.amount))} payment",
                    explanation=(
                        f"'{e.description}' on {d(e.entry_date) if e.entry_date else 'unknown date'} has no matching "
                        f"receipt in the monthly statement (payments from R$ {brl(threshold)} must be supported)."
                    ),
                    severity=Severity.MEDIUM,
                    amount=abs(e.amount),
                    period=month(e.entry_date),
                    evidence=(line_evidence(e),),
                )
            )
        return findings


@dataclass(frozen=True)
class ReceiptAmountMismatch:
    code: str = "RECEIPT_AMOUNT_MISMATCH"
    description: str = "The receipt must show the amount that left the account."

    def evaluate(self, ctx: AuditContext) -> list[FindingDraft]:
        findings = []
        for e in _debits(ctx):
            link = ctx.link_for(e.id)
            receipt = ctx.receipt(link.receipt_id) if link else None
            if receipt is None or receipt.amount is None or e.amount is None:
                continue
            diff = abs(e.amount) - receipt.amount
            if abs(diff) <= CENT:
                continue
            findings.append(
                FindingDraft(
                    rule_code=self.code,
                    subject=f"{e.id}:{receipt.id}",
                    title=f"Paid R$ {brl(abs(e.amount))}, receipt shows R$ {brl(receipt.amount)}",
                    explanation=(
                        f"The statement debits R$ {brl(abs(e.amount))} for '{e.description}', but the receipt from "
                        f"{receipt.payee or 'the payee'} is for R$ {brl(receipt.amount)} "
                        f"(difference R$ {brl(abs(diff))})."
                    ),
                    severity=Severity.HIGH,
                    amount=abs(diff),
                    period=month(e.entry_date),
                    evidence=(line_evidence(e), receipt_evidence(receipt)),
                )
            )
        return findings


@dataclass(frozen=True)
class DuplicatePayment:
    code: str = "DUPLICATE_PAYMENT"
    description: str = "Same payee and amount paid twice within a few days."

    def evaluate(self, ctx: AuditContext) -> list[FindingDraft]:
        window = int(ctx.setting("duplicate_window_days", 10))
        groups: dict[tuple[frozenset[str], Decimal], list[Entry]] = defaultdict(list)
        for e in _debits(ctx):
            tokens = frozenset(significant_tokens(e.description))
            if e.amount is not None and tokens and e.entry_date and e.category not in NO_RECEIPT_EXPECTED:
                groups[(tokens, abs(e.amount))].append(e)
        findings = []
        for (_, amount), entries in groups.items():
            entries.sort(key=lambda e: e.entry_date or date.min)
            for first, second in itertools.pairwise(entries):
                if first.entry_date is None or second.entry_date is None:
                    continue
                days = (second.entry_date - first.entry_date).days
                if days > window:
                    continue
                findings.append(
                    FindingDraft(
                        rule_code=self.code,
                        subject=f"{first.id}:{second.id}",
                        title=f"R$ {brl(amount)} paid twice in {days} days",
                        explanation=(
                            f"'{second.description}' was paid on {d(first.entry_date)} and again on "
                            f"{d(second.entry_date)} with the same amount."
                        ),
                        severity=Severity.HIGH,
                        amount=amount,
                        period=month(second.entry_date),
                        evidence=(line_evidence(first, "first payment"), line_evidence(second, "second payment")),
                    )
                )
        return findings


@dataclass(frozen=True)
class BudgetOverrun:
    code: str = "BUDGET_OVERRUN"
    description: str = "Spending per category above the approved budget plus tolerance."

    def evaluate(self, ctx: AuditContext) -> list[FindingDraft]:
        tolerance = Decimal(str(ctx.setting("budget_tolerance", "0.10")))
        months_by_year: dict[int, set[int]] = defaultdict(set)
        for doc in ctx.documents.values():
            if doc.type == "financial_statement" and doc.reference_period:
                months_by_year[doc.reference_period.year].add(doc.reference_period.month)
        spent: dict[tuple[int, str], Decimal] = defaultdict(Decimal)
        for e in _debits(ctx):
            if e.entry_date and e.category and e.amount is not None:
                spent[(e.entry_date.year, e.category)] += abs(e.amount)

        findings = []
        for item in ctx.budget:
            months = len(months_by_year.get(item.year, set()))
            if not months:
                continue
            budgeted = item.monthly_amount * months
            actual = spent.get((item.year, item.category), Decimal(0))
            if actual <= budgeted * (1 + tolerance):
                continue
            over = actual - budgeted
            findings.append(
                FindingDraft(
                    rule_code=self.code,
                    subject=f"{item.year}:{item.category}",
                    title=f"'{item.category}' is {over / budgeted:.0%} over budget in {item.year}",
                    explanation=(
                        f"{months} months of statements show R$ {brl(actual)} spent on '{item.category}', against "
                        f"R$ {brl(budgeted)} budgeted (R$ {brl(item.monthly_amount)}/month). Tolerance: {tolerance:.0%}."
                    ),
                    severity=Severity.MEDIUM,
                    amount=over,
                    period=str(item.year),
                    evidence=(
                        Evidence(
                            item.document_id,
                            item.page,
                            f"{item.category}: R$ {brl(item.monthly_amount)} por mês",
                            "approved budget",
                        ),
                    ),
                )
            )
        return findings


@dataclass(frozen=True)
class ForeignDocument:
    code: str = "FOREIGN_DOCUMENT"
    description: str = "Receipts must be issued to this condominium."

    GENERIC = frozenset({"CONDOMINIO", "EDIFICIO", "RESIDENCIAL", "CONJUNTO", "PREDIO"})

    def evaluate(self, ctx: AuditContext) -> list[FindingDraft]:
        own_digits = "".join(c for c in (ctx.condominium.tax_id or "") if c.isdigit())
        own_name = significant_tokens(ctx.condominium.name) - self.GENERIC
        findings = []
        for r in ctx.receipts:
            payer_tokens = significant_tokens(r.payer_name or "") - self.GENERIC
            digits = "".join(c for c in (r.payer_tax_id or "") if c.isdigit())
            name_differs = bool(payer_tokens) and not (payer_tokens & own_name)
            # Up to two different digits on a matching name is OCR noise, not another payer.
            tax_differs = (
                len(digits) == 14
                and len(own_digits) == 14
                and sum(a != b for a, b in zip(digits, own_digits, strict=True)) > 2
            )
            if not (name_differs or tax_differs):
                continue
            findings.append(
                FindingDraft(
                    rule_code=self.code,
                    subject=str(r.id),
                    title=f"Receipt issued to another payer: {r.payer_name or r.payer_tax_id}",
                    explanation=(
                        f"A receipt of R$ {brl(r.amount or Decimal(0))} in this condominium's statement names "
                        f"'{r.payer_name}' (CNPJ {r.payer_tax_id}) as the payer, not {ctx.condominium.name}. "
                        "The condominium may have paid someone else's bill."
                    ),
                    severity=Severity.HIGH,
                    amount=r.amount,
                    period=month(r.paid_on),
                    evidence=(receipt_evidence(r),),
                )
            )
        return findings
