"""Rules over governance: assembly approvals, agendas and penalties."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from condo_audit.audit.financial import CENT, line_evidence, month
from condo_audit.audit.model import AuditContext, Decision, Evidence, FindingDraft, Penalty, Severity
from condo_audit.extraction.text import normalize, significant_tokens
from condo_audit.formatting import brl, d

MIN_SUBJECT_OVERLAP = 2


def _decision_evidence(dec: Decision) -> Evidence:
    return Evidence(dec.document_id, dec.page, f"Item {dec.item_number} – {dec.subject}", "meeting minutes")


@dataclass(frozen=True)
class UnapprovedExpense:
    """Extraordinary expenses above the convention's limit need an assembly
    approval covering them (matching subject, approved before the payment,
    cumulative payments within the approved amount)."""

    code: str = "UNAPPROVED_EXPENSE"
    description: str = "Extraordinary expense above the spending limit without assembly approval."

    def evaluate(self, ctx: AuditContext) -> list[FindingDraft]:
        param = ctx.parameters.get("spending_limit")
        if param is None:
            return []
        limit = Decimal(str(param.value["amount"]))
        budgeted = {b.category for b in ctx.budget}
        candidates = sorted(
            (
                e
                for e in ctx.entries
                if e.kind == "transaction"
                and e.amount is not None
                and e.amount < 0
                and abs(e.amount) > limit
                and e.category not in budgeted
            ),
            key=lambda e: e.entry_date or date.min,
        )
        consumed: dict[tuple[int, int], Decimal] = defaultdict(Decimal)
        legal_basis = Evidence(param.document_id, param.page, param.excerpt, "convention")
        findings = []
        for e in candidates:
            if e.amount is None:
                continue
            tokens = significant_tokens(e.description)
            related = [
                dec for dec in ctx.decisions if len(tokens & significant_tokens(dec.subject)) >= MIN_SUBJECT_OVERLAP
            ]
            approvals = [
                dec
                for dec in related
                if dec.approved
                and (dec.meeting_date is None or e.entry_date is None or dec.meeting_date <= e.entry_date)
            ]
            covered = False
            for dec in approvals:
                key = (dec.document_id, dec.item_number)
                if dec.approved_amount is None or consumed[key] + abs(e.amount) <= dec.approved_amount + CENT:
                    consumed[key] += abs(e.amount)
                    covered = True
                    break
            if covered:
                continue
            if approvals:
                reason = "exceeds the amount approved by the assembly"
            elif related:
                reason = "was put to the assembly and NOT approved"
            else:
                reason = "has no assembly approval on record"
            findings.append(
                FindingDraft(
                    rule_code=self.code,
                    subject=str(e.id),
                    title=f"R$ {brl(abs(e.amount))} extraordinary expense {reason}",
                    explanation=(
                        f"'{e.description}' on {d(e.entry_date) if e.entry_date else '?'} is above the R$ {brl(limit)} "
                        f"the manager may spend without an assembly, and it {reason}."
                    ),
                    severity=Severity.HIGH,
                    amount=abs(e.amount),
                    period=month(e.entry_date),
                    evidence=(line_evidence(e), legal_basis, *(_decision_evidence(dec) for dec in related)),
                )
            )
        return findings


@dataclass(frozen=True)
class AgendaItemNotDeliberated:
    code: str = "AGENDA_ITEM_NOT_DELIBERATED"
    description: str = "Every item announced in the meeting notice must be deliberated in the minutes."

    def evaluate(self, ctx: AuditContext) -> list[FindingDraft]:
        decisions_by_date: dict[date | None, list[Decision]] = defaultdict(list)
        for dec in ctx.decisions:
            decisions_by_date[dec.meeting_date].append(dec)
        findings = []
        for item in ctx.agenda:
            if "ASSUNTOS GERAIS" in normalize(item.subject):
                continue
            decisions = decisions_by_date.get(item.meeting_date, [])
            if any(dec.item_number == item.item_number for dec in decisions) or any(
                len(significant_tokens(item.subject) & significant_tokens(dec.subject)) >= MIN_SUBJECT_OVERLAP
                for dec in decisions
            ):
                continue
            when = d(item.meeting_date) if item.meeting_date else "unknown date"
            findings.append(
                FindingDraft(
                    rule_code=self.code,
                    subject=f"{item.document_id}:{item.item_number}",
                    title=f"Agenda item {item.item_number} of the {when} meeting was never deliberated",
                    explanation=(
                        f"The meeting notice lists '{item.subject}', but "
                        + (
                            "no minutes were found for this meeting."
                            if not decisions
                            else "the minutes do not record it."
                        )
                    ),
                    severity=Severity.MEDIUM,
                    period=month(item.meeting_date),
                    evidence=(
                        Evidence(item.document_id, item.page, f"{item.item_number}. {item.subject}", "meeting notice"),
                    ),
                )
            )
        return findings


@dataclass(frozen=True)
class PenaltyLadderViolation:
    code: str = "PENALTY_LADDER_VIOLATION"
    description: str = "Penalties must follow the progressive steps defined in the bylaws."

    DEFAULT_LADDER = ("warning", "fine")

    def evaluate(self, ctx: AuditContext) -> list[FindingDraft]:
        param = ctx.parameters.get("penalty_ladder")
        ladder = list(param.value.get("steps", [])) if param else list(self.DEFAULT_LADDER)
        if not ladder:
            return []
        groups: dict[tuple[str, str], list[Penalty]] = defaultdict(list)
        for p in ctx.penalties:
            groups[(normalize(p.unit), normalize(p.infraction))].append(p)
        findings = []
        for notices in groups.values():
            notices.sort(key=lambda p: p.issued_on or date.min)
            for occurrence, p in enumerate(notices):
                expected = ladder[min(occurrence, len(ladder) - 1)]
                if expected != "warning" or p.kind != "fine":
                    continue
                basis = (Evidence(param.document_id, param.page, param.excerpt, "bylaws"),) if param else ()
                findings.append(
                    FindingDraft(
                        rule_code=self.code,
                        subject=f"{p.document_id}",
                        title=f"Unit {p.unit} fined on occurrence #{occurrence + 1}, a written warning was due",
                        explanation=(
                            f"'{p.infraction}' is occurrence #{occurrence + 1} for unit {p.unit}; the bylaws require a "
                            f"written warning at this step, but a fine of R$ {brl(p.amount or Decimal(0))} was issued."
                        ),
                        severity=Severity.MEDIUM,
                        amount=p.amount,
                        period=month(p.issued_on),
                        evidence=(
                            Evidence(
                                p.document_id, p.page, f"Unidade {p.unit} | {p.infraction} | multa", "penalty notice"
                            ),
                            *basis,
                        ),
                    )
                )
        return findings
