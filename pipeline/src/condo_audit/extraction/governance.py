"""Governing documents: budget, convention, bylaws, meeting notices and
minutes, penalty notices. Each extractor keeps the page it read from, so a
finding can cite its source."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any

from condo_audit.documents.layout import PageLayout
from condo_audit.extraction.categories import categorize
from condo_audit.extraction.fields import labeled_fields
from condo_audit.extraction.money import find_amounts, parse_brl
from condo_audit.extraction.text import clean_tokens, normalize, parse_date

# ---------------------------------------------------------------- budget


@dataclass(frozen=True, slots=True)
class BudgetLine:
    category: str
    label: str
    monthly_amount: Decimal
    page: int


def parse_budget(pages: list[PageLayout]) -> tuple[int | None, list[BudgetLine]]:
    year: int | None = None
    lines: list[BudgetLine] = []
    seen: set[str] = set()
    for page in pages:
        if year is None:
            found = re.search(r"OR[CÇ]AMENT[AÁ]RIA\s+(\d{4})", normalize(page.text))
            year = int(found.group(1)) if found else None
        for line in page.lines:
            text = clean_tokens(line.text)
            amounts = find_amounts(text)
            if len(amounts) != 1:
                continue
            amount, start, _ = amounts[0]
            label = text[:start].strip()
            category = categorize(label)
            if not label or "TOTAL" in normalize(label) or category is None or category in seen:
                continue
            seen.add(category)
            lines.append(BudgetLine(category, label, amount, page.number))
    return year, lines


# ---------------------------------------------------------------- notices & minutes


@dataclass(frozen=True, slots=True)
class AgendaItem:
    number: int
    subject: str
    page: int


@dataclass(frozen=True, slots=True)
class MeetingDecision:
    number: int
    subject: str
    deliberation: str
    approved: bool
    amount: Decimal | None
    page: int


def _joined(pages: list[PageLayout]) -> list[tuple[int, str]]:
    return [(p.number, " ".join(clean_tokens(line.text) for line in p.lines)) for p in pages]


def parse_meeting_notice(pages: list[PageLayout]) -> tuple[date | None, list[AgendaItem]]:
    meeting_date: date | None = None
    items: list[AgendaItem] = []
    for number, text in _joined(pages):
        if meeting_date is None:
            found = re.search(r"no dia\s+(\d{1,2}/\d{1,2}/\d{4})", text, re.IGNORECASE)
            meeting_date = parse_date(found.group(1)) if found else None
        for match in re.finditer(r"(?:^|\s)(\d{1,2})\.\s+([^;]{3,200});", text):
            items.append(AgendaItem(int(match.group(1)), match.group(2).strip(), number))
    return meeting_date, items


_ITEM_RE = re.compile(
    r"Item\s+(\d+)\s*[–—-]\s*(.+?)\.\s*Delibera[çc][ãa]o\s*:\s*(.+?)"
    r"(?=\s+Item\s+\d+\s*[–—-]|\s+Nada mais havendo|$)",
    re.IGNORECASE | re.DOTALL,
)
_REJECTED = re.compile(r"\b(n[ãa]o\s+aprovad|rejeitad|reprovad)", re.IGNORECASE)
_APPROVED = re.compile(r"\baprovad", re.IGNORECASE)


def parse_meeting_minutes(pages: list[PageLayout]) -> tuple[date | None, list[MeetingDecision]]:
    joined = _joined(pages)
    meeting_date = next((d for _, t in joined if (d := parse_date(t)) is not None), None)
    full = " ".join(t for _, t in joined)
    page_of = _page_locator(joined)
    decisions = []
    for match in _ITEM_RE.finditer(full):
        deliberation = " ".join(match.group(3).split())
        amount = parse_brl(deliberation)
        decisions.append(
            MeetingDecision(
                number=int(match.group(1)),
                subject=" ".join(match.group(2).split()),
                deliberation=deliberation,
                approved=bool(_APPROVED.search(deliberation)) and not _REJECTED.search(deliberation),
                amount=amount,
                page=page_of(match.start()),
            )
        )
    return meeting_date, decisions


def _page_locator(joined: list[tuple[int, str]]) -> Any:
    bounds: list[tuple[int, int]] = []
    offset = 0
    for number, text in joined:
        offset += len(text) + 1
        bounds.append((offset, number))

    def locate(position: int) -> int:
        return next((n for end, n in bounds if position < end), joined[-1][0] if joined else 1)

    return locate


# ---------------------------------------------------------------- bylaws & convention


@dataclass(frozen=True, slots=True)
class Clause:
    number: str
    text: str
    page: int


@dataclass(frozen=True, slots=True)
class Parameter:
    key: str
    value: dict[str, Any]
    excerpt: str
    page: int


_CLAUSE_RE = re.compile(r"(?:^|\s)(\d{1,2}\.\d{1,2})\s*-\s+(.+?)(?=\s\d{1,2}\.\d{1,2}\s*-\s|\sCAP[ÍI]TULO\s|$)")


def parse_bylaws(pages: list[PageLayout]) -> tuple[list[Clause], list[Parameter]]:
    clauses = []
    params = []
    for number, text in _joined(pages):
        for match in _CLAUSE_RE.finditer(text):
            clause = Clause(match.group(1), match.group(2).strip(), number)
            clauses.append(clause)
            ladder = _penalty_ladder(clause.text)
            if ladder:
                params.append(
                    Parameter(
                        "penalty_ladder",
                        {"steps": ladder, "clause": clause.number},
                        f"{clause.number} - {clause.text}",
                        number,
                    )
                )
    return clauses, params


def _penalty_ladder(text: str) -> list[str]:
    if "gradação" not in text.lower() and "gradacao" not in normalize(text).lower():
        return []
    steps = re.split(r"\b[a-h]\)\s*", text)[1:]
    return ["warning" if "advert" in normalize(step).lower() else "fine" for step in steps]


_LIMIT_RE = re.compile(
    r"despesas\s+extraordin[áa]rias\s+at[ée]\s+o\s+limite\s+de\s+R\$\s*([\d.\s]+,\d{2})", re.IGNORECASE
)


def parse_convention(pages: list[PageLayout]) -> list[Parameter]:
    for number, text in _joined(pages):
        match = _LIMIT_RE.search(text)
        if match:
            limit = parse_brl(match.group(1))
            sentence_start = text.rfind("Art.", 0, match.start())
            sentence_end = text.find(".", match.end())
            excerpt = text[max(sentence_start, 0) : sentence_end + 1 if sentence_end > 0 else None].strip()
            if limit is not None:
                return [Parameter("spending_limit", {"amount": f"{limit:.2f}"}, excerpt, number)]
    return []


# ---------------------------------------------------------------- penalty notices


@dataclass(frozen=True, slots=True)
class PenaltyData:
    unit: str
    infraction: str
    kind: str  # warning | fine
    amount: Decimal | None
    issued_on: date | None
    page: int


def parse_penalty_notice(pages: list[PageLayout]) -> PenaltyData | None:
    for page in pages:
        f = {k: v for k, (v, _) in labeled_fields(page).items()}
        if "UNIDADE" not in f or "INFRACAO" not in f:
            continue
        penalty = normalize(f.get("PENALIDADE APLICADA", f.get("PENALIDADE", "")))
        return PenaltyData(
            unit=f["UNIDADE"].strip(),
            infraction=f["INFRACAO"].strip(),
            kind="warning" if "ADVERT" in penalty else "fine",
            amount=parse_brl(f.get("VALOR", "")),
            issued_on=parse_date(f.get("DATA", "")),
            page=page.number,
        )
    return None
