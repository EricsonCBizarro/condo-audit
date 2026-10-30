"""`audit.run` handler: load the context, run the rules, persist findings.

Findings are upserted by fingerprint (rule + subject), so re-running the
audit never duplicates them and never resets a human review. Findings the
latest run no longer produces are marked inactive, not deleted.
"""

from __future__ import annotations

import json
from collections import Counter
from typing import Any
from uuid import UUID

from condo_audit.audit import model as m
from condo_audit.audit.registry import RULE_CODES, select
from condo_audit.db import Connection, Database
from condo_audit.jobs import JobMessage
from condo_audit.log import get_logger

log = get_logger(__name__)


def load_context(conn: Connection, condominium_id: int) -> m.AuditContext:
    c = conn.execute("select id, name, tax_id, settings from condominiums where id = %s", (condominium_id,)).fetchone()
    if c is None:
        raise LookupError(f"condominium {condominium_id} not found")
    ctx = m.AuditContext(m.Condominium(c["id"], c["name"], c["tax_id"], c["settings"] or {}))

    def rows(sql: str) -> list[dict[str, Any]]:
        return conn.execute(sql, {"c": condominium_id}).fetchall()

    for r in rows("select * from documents where condominium_id = %(c)s and status = 'processed'"):
        ctx.documents[r["id"]] = m.Document(r["id"], r["type"], r["title"], r["reference_period"])

    ctx.entries = [
        m.Entry(
            r["id"],
            r["document_id"],
            r["page_number"],
            r["line_number"],
            r["kind"],
            r["entry_date"],
            r["description"],
            r["amount"],
            r["balance"],
            r["category"],
            r["reconciliation"],
            float(r["confidence"]),
            r["raw_text"],
        )
        for r in rows(
            "select * from statement_entries where condominium_id = %(c)s and document_id in "
            "(select id from documents where condominium_id = %(c)s and status = 'processed')"
        )
    ]
    ctx.receipts = [
        m.Receipt(
            r["id"],
            r["document_id"],
            r["page_number"],
            r["payee"],
            r["payer_name"],
            r["payer_tax_id"],
            r["amount"],
            r["paid_on"],
        )
        for r in rows(
            "select * from receipts where condominium_id = %(c)s and document_id in "
            "(select id from documents where condominium_id = %(c)s and status = 'processed')"
        )
    ]
    ctx.links = [
        m.Link(r["statement_entry_id"], r["receipt_id"], r["score"], r["status"])
        for r in rows(
            "select l.* from entry_receipt_links l join statement_entries e on e.id = l.statement_entry_id "
            "where e.condominium_id = %(c)s"
        )
    ]
    ctx.budget = [
        m.BudgetItem(r["document_id"], r["year"], r["category"], r["monthly_amount"], r["page_number"])
        for r in rows("select * from budget_items where condominium_id = %(c)s")
    ]
    ctx.decisions = [
        m.Decision(
            r["document_id"],
            r["meeting_date"],
            r["item_number"],
            r["subject"],
            r["approved"],
            r["approved_amount"],
            r["page_number"],
        )
        for r in rows("select * from meeting_decisions where condominium_id = %(c)s")
    ]
    ctx.agenda = [
        m.AgendaItem(r["document_id"], r["meeting_date"], r["item_number"], r["subject"], r["page_number"])
        for r in rows("select * from agenda_items where condominium_id = %(c)s")
    ]
    for r in rows("select * from governance_parameters where condominium_id = %(c)s order by id"):
        ctx.parameters[r["key"]] = m.Parameter(
            r["document_id"], r["key"], r["value"], r["source_excerpt"], r["page_number"]
        )
    ctx.penalties = [
        m.Penalty(
            r["document_id"], r["unit"], r["infraction"], r["kind"], r["amount"], r["issued_on"], r["page_number"]
        )
        for r in rows("select * from penalty_notices where condominium_id = %(c)s")
    ]
    return ctx


def persist_findings(
    conn: Connection, condominium_id: int, run_id: UUID | None, drafts: list[m.FindingDraft], rule_codes: set[str]
) -> dict[str, int]:
    fingerprints = []
    for f in drafts:
        fingerprints.append(f.fingerprint)
        conn.execute(
            """
            insert into findings (condominium_id, last_audit_run_id, rule_code, category, severity, title, explanation,
                amount, period, evidence, fingerprint, status, is_active, first_detected_at, last_detected_at,
                created_at, updated_at)
            values (%(c)s, %(run)s, %(rule)s, %(cat)s, %(sev)s, %(title)s, %(expl)s, %(amount)s, %(period)s,
                %(evidence)s::jsonb, %(fp)s, 'open', true, now(), now(), now(), now())
            on conflict (condominium_id, fingerprint) do update set
                last_audit_run_id = excluded.last_audit_run_id, category = excluded.category,
                severity = excluded.severity, title = excluded.title, explanation = excluded.explanation,
                amount = excluded.amount, period = excluded.period, evidence = excluded.evidence,
                is_active = true, last_detected_at = now(), updated_at = now()
            """,
            {
                "c": condominium_id,
                "run": str(run_id) if run_id else None,
                "rule": f.rule_code,
                "cat": f.category.value,
                "sev": f.severity.value,
                "title": f.title[:255],
                "expl": f.explanation,
                "amount": f.amount,
                "period": f.period,
                "evidence": json.dumps([e.as_dict() for e in f.evidence]),
                "fp": f.fingerprint,
            },
        )
    deactivated = conn.execute(
        """
        update findings set is_active = false, updated_at = now()
        where condominium_id = %s and is_active and rule_code = any(%s) and not (fingerprint = any(%s))
        """,
        (condominium_id, sorted(rule_codes), fingerprints),
    ).rowcount
    return {"findings": len(drafts), "deactivated": deactivated}


class AuditRunner:
    def __init__(self, db: Database) -> None:
        self._db = db

    def run(
        self, condominium_id: int, rule_codes: list[str] | None = None, run_id: UUID | None = None
    ) -> dict[str, Any]:
        rules = select(rule_codes)
        with self._db.transaction() as conn:
            ctx = load_context(conn, condominium_id)
            drafts = [draft for rule in rules for draft in rule.evaluate(ctx)]
            codes = {code for rule in rules for code in RULE_CODES.get(rule.code, (rule.code,))}
            stats = persist_findings(conn, condominium_id, run_id, drafts, codes)
        by_rule = Counter(d.rule_code for d in drafts)
        log.info("audit.completed", findings=len(drafts), rules=len(rules))
        return {**stats, "rules": len(rules), "by_rule": dict(by_rule)}

    def handle(self, message: JobMessage) -> dict[str, Any]:
        rules = message.payload.get("rules")
        return self.run(message.condominium_id, list(rules) if rules else None, message.job_id)
