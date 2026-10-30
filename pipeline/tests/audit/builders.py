"""Tiny builders so each rule test reads like the scenario it checks."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from itertools import count
from typing import Any

from condo_audit.audit import model as m

_ids = count(1)
D = Decimal


def context(**settings: Any) -> m.AuditContext:
    return m.AuditContext(m.Condominium(1, "Condomínio Residencial Exemplo", "12.345.678/0001-00", settings))


def statement(ctx: m.AuditContext, period: date) -> int:
    doc_id = next(_ids)
    ctx.documents[doc_id] = m.Document(doc_id, "financial_statement", f"Statement {period:%m/%Y}", period)
    return doc_id


def entry(
    ctx: m.AuditContext,
    doc: int,
    description: str,
    amount: str | None,
    balance: str | None,
    when: date | None = None,
    kind: str = "transaction",
    reconciliation: str = "ok",
    category: str | None = None,
    confidence: float = 0.98,
) -> m.Entry:
    e = m.Entry(
        id=next(_ids),
        document_id=doc,
        page=1,
        line=len(ctx.entries) + 1,
        kind=kind,
        entry_date=when,
        description=description,
        amount=D(amount) if amount else None,
        balance=D(balance) if balance else None,
        category=category,
        reconciliation=reconciliation,
        confidence=confidence,
        raw_text=description,
    )
    ctx.entries.append(e)
    return e


def receipt(
    ctx: m.AuditContext,
    doc: int,
    payee: str,
    amount: str,
    when: date,
    payer: str | None = None,
    tax_id: str | None = None,
) -> m.Receipt:
    r = m.Receipt(
        next(_ids), doc, 2, payee, payer or ctx.condominium.name, tax_id or ctx.condominium.tax_id, D(amount), when
    )
    ctx.receipts.append(r)
    return r


def link(ctx: m.AuditContext, e: m.Entry, r: m.Receipt, status: str = "suggested") -> None:
    ctx.links.append(m.Link(e.id, r.id, D("1.0"), status))
