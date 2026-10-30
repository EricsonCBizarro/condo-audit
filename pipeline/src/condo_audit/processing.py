"""`document.process` handler: bronze → silver → gold for one document.

Derived rows are rebuilt inside a single transaction, so a document is never
left half-processed. Rows that people may have reviewed (statement entries,
receipts, entry↔receipt links) are upserted by natural key instead of being
deleted, which keeps their ids and the human decisions attached to them.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from condo_audit.db import Connection, Database
from condo_audit.documents.layout import PageLayout
from condo_audit.documents.reader import DocumentReader
from condo_audit.extraction import governance as gov
from condo_audit.extraction.categories import categorize
from condo_audit.extraction.pages import PageType, classify_page
from condo_audit.extraction.receipts import ReceiptData, parse_receipt
from condo_audit.extraction.statement import RowKind, StatementRow, parse_rows
from condo_audit.jobs import JobMessage
from condo_audit.linking import link_document
from condo_audit.log import get_logger
from condo_audit.storage import DocumentStore

log = get_logger(__name__)


class DocumentNotFoundError(LookupError):
    pass


@dataclass(frozen=True, slots=True)
class DocumentRow:
    id: int
    condominium_id: int
    type: str
    storage_key: str
    settings: dict[str, Any]


class DocumentProcessor:
    def __init__(self, db: Database, store: DocumentStore, reader: DocumentReader) -> None:
        self._db = db
        self._store = store
        self._reader = reader

    def handle(self, message: JobMessage) -> dict[str, Any]:
        document_id = int(message.payload["document_id"])
        doc = self._load(document_id, message.condominium_id)
        self._set_status(doc.id, "processing")
        try:
            pages = list(self._reader.pages(self._store.get(doc.storage_key)))
            page_types = {p.number: classify_page(p) for p in pages}
            with self._db.transaction() as conn:
                self._write_pages(conn, doc.id, pages, page_types)
                stats = self._extract(conn, doc, pages, page_types)
                sources = {p.source for p in pages}
                conn.execute(
                    """
                    update documents set status = 'processed', page_count = %(pages)s, text_source = %(source)s,
                        processed_at = now(), updated_at = now(),
                        metadata = metadata || jsonb_build_object('extraction', %(stats)s::jsonb)
                    where id = %(id)s
                    """,
                    {
                        "id": doc.id,
                        "pages": len(pages),
                        "source": sources.pop() if len(sources) == 1 else "mixed",
                        "stats": json.dumps(stats, default=str),
                    },
                )
        except Exception:
            self._set_status(doc.id, "failed")
            raise
        ocr_pages = sum(1 for p in pages if p.source == "ocr")
        return {"document_id": doc.id, "pages": len(pages), "ocr_pages": ocr_pages, **stats}

    # ------------------------------------------------------------------ io

    def _load(self, document_id: int, condominium_id: int) -> DocumentRow:
        with self._db.transaction() as conn:
            row = conn.execute(
                """
                select d.id, d.condominium_id, d.type, d.storage_key, c.settings
                from documents d join condominiums c on c.id = d.condominium_id
                where d.id = %s and d.condominium_id = %s
                """,
                (document_id, condominium_id),
            ).fetchone()
        if row is None:  # never trust a job to cross tenants
            raise DocumentNotFoundError(f"document {document_id} not found in condominium {condominium_id}")
        return DocumentRow(
            int(str(row["id"])),
            int(str(row["condominium_id"])),
            str(row["type"]),
            str(row["storage_key"]),
            dict(row["settings"] or {}),
        )

    def _set_status(self, document_id: int, status: str) -> None:
        with self._db.transaction() as conn:
            conn.execute("update documents set status = %s, updated_at = now() where id = %s", (status, document_id))

    @staticmethod
    def _write_pages(conn: Connection, document_id: int, pages: list[PageLayout], types: dict[int, PageType]) -> None:
        conn.execute("delete from document_pages where document_id = %s", (document_id,))
        for page in pages:
            page_id = conn.execute(
                """
                insert into document_pages
                    (document_id, page_number, page_type, text_source, text, mean_confidence, created_at, updated_at)
                values (%s, %s, %s, %s, %s, %s, now(), now()) returning id
                """,
                (document_id, page.number, types[page.number].value, page.source, page.text, page.mean_confidence),
            ).fetchone()
            if page_id is None:  # pragma: no cover - INSERT ... RETURNING always returns a row
                raise RuntimeError("page insert returned nothing")
            with conn.cursor() as cur:
                cur.executemany(
                    """
                    insert into page_lines (document_page_id, line_number, text, bbox, confidence)
                    values (%s, %s, %s, %s, %s)
                    """,
                    [
                        (page_id["id"], i, line.text, json.dumps([round(v, 1) for v in line.bbox]), line.confidence)
                        for i, line in enumerate(page.lines, start=1)
                    ],
                )

    # ------------------------------------------------------------------ extraction

    def _extract(
        self, conn: Connection, doc: DocumentRow, pages: list[PageLayout], types: dict[int, PageType]
    ) -> dict[str, Any]:
        match doc.type:
            case "financial_statement":
                return self._statement(conn, doc, pages, types)
            case "budget":
                return self._budget(conn, doc, pages)
            case "meeting_notice":
                return self._notice(conn, doc, pages)
            case "meeting_minutes":
                return self._minutes(conn, doc, pages)
            case "bylaws":
                clauses, params = gov.parse_bylaws(pages)
                self._replace_clauses(conn, doc, clauses)
                self._replace_parameters(conn, doc, params)
                return {"clauses": len(clauses), "parameters": len(params)}
            case "convention":
                params = gov.parse_convention(pages)
                self._replace_parameters(conn, doc, params)
                return {"parameters": len(params)}
            case "penalty_notice":
                return self._penalty(conn, doc, pages)
            case _:
                return {}

    def _statement(
        self, conn: Connection, doc: DocumentRow, pages: list[PageLayout], types: dict[int, PageType]
    ) -> dict[str, Any]:
        rows = parse_rows([p for p in pages if types[p.number] is PageType.STATEMENT])
        receipts = [parse_receipt(p) for p in pages if types[p.number] is PageType.RECEIPT]
        keywords = doc.settings.get("category_keywords")
        self._upsert_entries(conn, doc, rows, keywords)
        self._upsert_receipts(conn, doc, receipts)
        links = link_document(conn, doc.id)
        inconsistent = sum(1 for r in rows if r.reconciliation.value == "inconsistent")
        return {"statement_rows": len(rows), "receipts": len(receipts), "links": links, "inconsistent": inconsistent}

    @staticmethod
    def _upsert_entries(
        conn: Connection, doc: DocumentRow, rows: list[StatementRow], keywords: dict[str, list[str]] | None
    ) -> None:
        keys = []
        for row in rows:
            category = (
                categorize(row.description, keywords)
                if row.kind is RowKind.TRANSACTION and row.amount is not None and row.amount < 0
                else None
            )
            keys.append((row.page, row.line))
            conn.execute(
                """
                insert into statement_entries (condominium_id, document_id, page_number, line_number, kind, entry_date,
                    description, amount, balance, category, reconciliation, confidence, raw_text, created_at, updated_at)
                values (%(c)s, %(d)s, %(p)s, %(l)s, %(kind)s, %(date)s, %(desc)s, %(amount)s, %(balance)s, %(cat)s,
                    %(rec)s, %(conf)s, %(raw)s, now(), now())
                on conflict (document_id, page_number, line_number) do update set
                    kind = excluded.kind, entry_date = excluded.entry_date, description = excluded.description,
                    amount = excluded.amount, balance = excluded.balance, category = excluded.category,
                    reconciliation = excluded.reconciliation, confidence = excluded.confidence,
                    raw_text = excluded.raw_text, updated_at = now()
                """,
                {
                    "c": doc.condominium_id,
                    "d": doc.id,
                    "p": row.page,
                    "l": row.line,
                    "kind": row.kind.value,
                    "date": row.entry_date,
                    "desc": row.description[:255],
                    "amount": row.amount,
                    "balance": row.balance,
                    "cat": category,
                    "rec": row.reconciliation.value,
                    "conf": row.confidence,
                    "raw": row.raw_text,
                },
            )
        _delete_missing(conn, "statement_entries", doc.id, ["page_number", "line_number"], keys)

    @staticmethod
    def _upsert_receipts(conn: Connection, doc: DocumentRow, receipts: list[ReceiptData]) -> None:
        for r in receipts:
            conn.execute(
                """
                insert into receipts (condominium_id, document_id, page_number, payee, payer_name, payer_tax_id, amount,
                    paid_on, description, confidence, created_at, updated_at)
                values (%(c)s, %(d)s, %(p)s, %(payee)s, %(payer)s, %(tax)s, %(amount)s, %(paid)s, %(desc)s, %(conf)s,
                    now(), now())
                on conflict (document_id, page_number) do update set
                    payee = excluded.payee, payer_name = excluded.payer_name, payer_tax_id = excluded.payer_tax_id,
                    amount = excluded.amount, paid_on = excluded.paid_on, description = excluded.description,
                    confidence = excluded.confidence, updated_at = now()
                """,
                {
                    "c": doc.condominium_id,
                    "d": doc.id,
                    "p": r.page,
                    "payee": r.payee,
                    "payer": r.payer_name,
                    "tax": r.payer_tax_id,
                    "amount": r.amount,
                    "paid": r.paid_on,
                    "desc": (r.description or "")[:255] or None,
                    "conf": r.confidence,
                },
            )
        _delete_missing(conn, "receipts", doc.id, ["page_number"], [(r.page,) for r in receipts])

    @staticmethod
    def _budget(conn: Connection, doc: DocumentRow, pages: list[PageLayout]) -> dict[str, Any]:
        year, lines = gov.parse_budget(pages)
        conn.execute("delete from budget_items where document_id = %s", (doc.id,))
        for line in lines:
            conn.execute(
                """
                insert into budget_items (condominium_id, document_id, year, category, monthly_amount, page_number,
                    created_at, updated_at)
                values (%s, %s, %s, %s, %s, %s, now(), now())
                """,
                (
                    doc.condominium_id,
                    doc.id,
                    year or datetime.now(UTC).year,
                    line.category,
                    line.monthly_amount,
                    line.page,
                ),
            )
        return {"budget_lines": len(lines), "year": year}

    @staticmethod
    def _notice(conn: Connection, doc: DocumentRow, pages: list[PageLayout]) -> dict[str, Any]:
        meeting_date, items = gov.parse_meeting_notice(pages)
        conn.execute("delete from agenda_items where document_id = %s", (doc.id,))
        for item in items:
            conn.execute(
                """
                insert into agenda_items (condominium_id, document_id, meeting_date, item_number, subject, page_number,
                    created_at, updated_at)
                values (%s, %s, %s, %s, %s, %s, now(), now()) on conflict (document_id, item_number) do nothing
                """,
                (doc.condominium_id, doc.id, meeting_date, item.number, item.subject, item.page),
            )
        return {"agenda_items": len(items), "meeting_date": meeting_date}

    @staticmethod
    def _minutes(conn: Connection, doc: DocumentRow, pages: list[PageLayout]) -> dict[str, Any]:
        meeting_date, decisions = gov.parse_meeting_minutes(pages)
        conn.execute("delete from meeting_decisions where document_id = %s", (doc.id,))
        for dec in decisions:
            conn.execute(
                """
                insert into meeting_decisions (condominium_id, document_id, meeting_date, item_number, subject,
                    approved, approved_amount, page_number, created_at, updated_at)
                values (%s, %s, %s, %s, %s, %s, %s, %s, now(), now()) on conflict (document_id, item_number) do nothing
                """,
                (
                    doc.condominium_id,
                    doc.id,
                    meeting_date,
                    dec.number,
                    f"{dec.subject}. {dec.deliberation}",
                    dec.approved,
                    dec.amount,
                    dec.page,
                ),
            )
        return {"decisions": len(decisions), "meeting_date": meeting_date}

    @staticmethod
    def _replace_clauses(conn: Connection, doc: DocumentRow, clauses: list[gov.Clause]) -> None:
        conn.execute("delete from bylaw_clauses where document_id = %s", (doc.id,))
        for clause in clauses:
            conn.execute(
                """
                insert into bylaw_clauses (condominium_id, document_id, number, text, page_number, created_at, updated_at)
                values (%s, %s, %s, %s, %s, now(), now()) on conflict (document_id, number) do nothing
                """,
                (doc.condominium_id, doc.id, clause.number, clause.text, clause.page),
            )

    @staticmethod
    def _replace_parameters(conn: Connection, doc: DocumentRow, params: list[gov.Parameter]) -> None:
        conn.execute("delete from governance_parameters where document_id = %s", (doc.id,))
        for p in params:
            conn.execute(
                """
                insert into governance_parameters (condominium_id, document_id, key, value, source_excerpt, page_number,
                    created_at, updated_at)
                values (%s, %s, %s, %s::jsonb, %s, %s, now(), now()) on conflict (document_id, key) do nothing
                """,
                (doc.condominium_id, doc.id, p.key, json.dumps(p.value), p.excerpt, p.page),
            )

    @staticmethod
    def _penalty(conn: Connection, doc: DocumentRow, pages: list[PageLayout]) -> dict[str, Any]:
        data = gov.parse_penalty_notice(pages)
        conn.execute("delete from penalty_notices where document_id = %s", (doc.id,))
        if data is None:
            return {"penalty": False}
        conn.execute(
            """
            insert into penalty_notices (condominium_id, document_id, unit, infraction, kind, amount, issued_on,
                page_number, created_at, updated_at)
            values (%s, %s, %s, %s, %s, %s, %s, %s, now(), now())
            """,
            (doc.condominium_id, doc.id, data.unit, data.infraction, data.kind, data.amount, data.issued_on, data.page),
        )
        return {"penalty": True, "unit": data.unit, "kind": data.kind}


def _delete_missing(
    conn: Connection, table: str, document_id: int, columns: list[str], keep: list[tuple[Any, ...]]
) -> None:
    """Delete this document's rows whose natural key is no longer extracted."""
    if not keep:
        conn.execute(f"delete from {table} where document_id = %s", (document_id,))  # noqa: S608
        return
    key = ", ".join(columns)
    placeholders = ", ".join(["(" + ", ".join(["%s"] * len(columns)) + ")"] * len(keep))
    params: list[Any] = [document_id, *[v for row in keep for v in row]]
    conn.execute(
        f"delete from {table} where document_id = %s and ({key}) not in ({placeholders})",  # noqa: S608
        params,
    )
