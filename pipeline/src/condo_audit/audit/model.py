"""Data the rules read (AuditContext) and what they produce (FindingDraft).

Rules are pure functions of the context: no database, no I/O. That keeps each
rule unit-testable with a handful of hand-built objects.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Any, Protocol


class Severity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Category(StrEnum):
    IRREGULARITY = "irregularity"
    DATA_QUALITY = "data_quality"


@dataclass(frozen=True, slots=True)
class Evidence:
    document_id: int
    page: int
    excerpt: str
    label: str = "source"

    def as_dict(self) -> dict[str, Any]:
        return {"document_id": self.document_id, "page": self.page, "excerpt": self.excerpt, "label": self.label}


@dataclass(frozen=True, slots=True)
class FindingDraft:
    rule_code: str
    subject: str  # what the finding is about; with rule_code it forms the fingerprint
    title: str
    explanation: str
    severity: Severity
    category: Category = Category.IRREGULARITY
    amount: Decimal | None = None
    period: str | None = None
    evidence: tuple[Evidence, ...] = ()

    @property
    def fingerprint(self) -> str:
        return hashlib.sha256(f"{self.rule_code}|{self.subject}".encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class Document:
    id: int
    type: str
    title: str
    reference_period: date | None


@dataclass(frozen=True, slots=True)
class Entry:
    id: int
    document_id: int
    page: int
    line: int
    kind: str
    entry_date: date | None
    description: str
    amount: Decimal | None
    balance: Decimal | None
    category: str | None
    reconciliation: str
    confidence: float
    raw_text: str


@dataclass(frozen=True, slots=True)
class Receipt:
    id: int
    document_id: int
    page: int
    payee: str | None
    payer_name: str | None
    payer_tax_id: str | None
    amount: Decimal | None
    paid_on: date | None


@dataclass(frozen=True, slots=True)
class Link:
    entry_id: int
    receipt_id: int
    score: Decimal
    status: str


@dataclass(frozen=True, slots=True)
class BudgetItem:
    document_id: int
    year: int
    category: str
    monthly_amount: Decimal
    page: int


@dataclass(frozen=True, slots=True)
class Decision:
    document_id: int
    meeting_date: date | None
    item_number: int
    subject: str
    approved: bool
    approved_amount: Decimal | None
    page: int


@dataclass(frozen=True, slots=True)
class AgendaItem:
    document_id: int
    meeting_date: date | None
    item_number: int
    subject: str
    page: int


@dataclass(frozen=True, slots=True)
class Parameter:
    document_id: int
    key: str
    value: dict[str, Any]
    excerpt: str
    page: int


@dataclass(frozen=True, slots=True)
class Penalty:
    document_id: int
    unit: str
    infraction: str
    kind: str
    amount: Decimal | None
    issued_on: date | None
    page: int


@dataclass(frozen=True, slots=True)
class Condominium:
    id: int
    name: str
    tax_id: str | None
    settings: dict[str, Any]


@dataclass
class AuditContext:
    condominium: Condominium
    documents: dict[int, Document] = field(default_factory=dict)
    entries: list[Entry] = field(default_factory=list)
    receipts: list[Receipt] = field(default_factory=list)
    links: list[Link] = field(default_factory=list)
    budget: list[BudgetItem] = field(default_factory=list)
    decisions: list[Decision] = field(default_factory=list)
    agenda: list[AgendaItem] = field(default_factory=list)
    parameters: dict[str, Parameter] = field(default_factory=dict)
    penalties: list[Penalty] = field(default_factory=list)

    def setting(self, key: str, default: Any) -> Any:
        return self.condominium.settings.get(key, default)

    def receipt(self, receipt_id: int) -> Receipt | None:
        return next((r for r in self.receipts if r.id == receipt_id), None)

    def link_for(self, entry_id: int) -> Link | None:
        return next((lk for lk in self.links if lk.entry_id == entry_id and lk.status != "rejected"), None)


class Rule(Protocol):
    @property
    def code(self) -> str: ...

    @property
    def description(self) -> str: ...

    def evaluate(self, ctx: AuditContext) -> list[FindingDraft]: ...
