from __future__ import annotations

from typing import Any

import pytest

from condo_audit.audit.runner import AuditRunner
from condo_audit.db import Database
from condo_audit.documents.layout import Word
from condo_audit.documents.reader import DocumentReader
from condo_audit.evaluation.loader import load_findings
from condo_audit.processing import DocumentNotFoundError, DocumentProcessor
from condo_audit.report.markdown import render as render_report
from condo_audit.synth import render, texts
from condo_audit.synth.scenario import build_world
from tests.integration.conftest import MemoryStore, add_document, process_message

pytestmark = pytest.mark.integration


class NoOcr:
    def words(self, image: Any, scale: float) -> list[Word]:  # pragma: no cover - native PDFs only
        raise AssertionError("native PDFs must not hit OCR")


@pytest.fixture(scope="module")
def world() -> Any:
    return build_world(42)[0]  # the condominium with planted irregularities


def _processor(db: Database, store: MemoryStore) -> DocumentProcessor:
    return DocumentProcessor(db, store, DocumentReader(NoOcr()))


def _march(db: Database, condo: dict[str, Any], store: MemoryStore, world: Any) -> int:
    store.objects["march"] = render.financial_statement(world, world.statements[2])
    return add_document(db, condo["id"], "financial_statement", "march", "2025-03-01")


def test_processing_extracts_reconciles_and_links(db: Database, condominium: dict[str, Any], world: Any) -> None:
    store = MemoryStore()
    doc_id = _march(db, condominium, store, world)

    stats = _processor(db, store).handle(process_message(condominium["id"], doc_id))

    assert stats["inconsistent"] == 1  # the planted 1.200,00 break
    assert stats["receipts"] == stats["links"] > 0
    with db.transaction() as conn:
        doc = conn.execute("select status, text_source, page_count from documents where id = %s", (doc_id,)).fetchone()
    assert doc == {"status": "processed", "text_source": "native", "page_count": stats["pages"]}


def test_reprocessing_keeps_ids_and_human_decisions(db: Database, condominium: dict[str, Any], world: Any) -> None:
    store = MemoryStore()
    doc_id = _march(db, condominium, store, world)
    processor = _processor(db, store)
    processor.handle(process_message(condominium["id"], doc_id))
    with db.transaction() as conn:
        entry_ids = [
            r["id"]
            for r in conn.execute("select id from statement_entries where document_id = %s order by id", (doc_id,))
        ]
        link = conn.execute(
            "update entry_receipt_links set status = 'confirmed', origin = 'manual' where id = "
            "(select min(l.id) from entry_receipt_links l join statement_entries e on e.id = l.statement_entry_id "
            "where e.document_id = %s) returning id",
            (doc_id,),
        ).fetchone()

    processor.handle(process_message(condominium["id"], doc_id))

    with db.transaction() as conn:
        again = [
            r["id"]
            for r in conn.execute("select id from statement_entries where document_id = %s order by id", (doc_id,))
        ]
        status = conn.execute("select status from entry_receipt_links where id = %s", (link["id"],)).fetchone()  # type: ignore[index]
    assert again == entry_ids
    assert status == {"status": "confirmed"}


def test_a_job_cannot_process_another_tenants_document(db: Database, condominium: dict[str, Any], world: Any) -> None:
    store = MemoryStore()
    doc_id = _march(db, condominium, store, world)
    with pytest.raises(DocumentNotFoundError):
        _processor(db, store).handle(process_message(condominium["id"] + 10_000, doc_id))


def test_audit_is_idempotent_and_preserves_reviews(db: Database, condominium: dict[str, Any], world: Any) -> None:
    store = MemoryStore()
    doc_id = _march(db, condominium, store, world)
    store.objects["convention"] = render.text_document("Convenção", texts.convention(world))
    conv_id = add_document(db, condominium["id"], "convention", "convention")
    processor = _processor(db, store)
    processor.handle(process_message(condominium["id"], doc_id))
    processor.handle(process_message(condominium["id"], conv_id))
    runner = AuditRunner(db)

    first = runner.run(condominium["id"])
    with db.transaction() as conn:
        finding = conn.execute(
            "update findings set status = 'dismissed' where condominium_id = %s and rule_code = 'BALANCE_CHAIN_BREAK' "
            "returning id, period",
            (condominium["id"],),
        ).fetchone()
    assert finding is not None
    assert finding["period"] == "2025-03"

    second = runner.run(condominium["id"])
    assert second["findings"] == first["findings"]
    with db.transaction() as conn:
        row = conn.execute("select status, is_active from findings where id = %s", (finding["id"],)).fetchone()
        total = conn.execute(
            "select count(*) as n from findings where condominium_id = %s", (condominium["id"],)
        ).fetchone()
        assert row == {"status": "dismissed", "is_active": True}
        assert total is not None
        assert total["n"] == first["findings"]

        # The cause disappears (e.g. a corrected statement): the finding is deactivated, not deleted.
        conn.execute("update statement_entries set reconciliation = 'ok' where document_id = %s", (doc_id,))
    runner.run(condominium["id"], ["BALANCE_CHAIN_BREAK"])
    with db.transaction() as conn:
        row = conn.execute("select is_active from findings where id = %s", (finding["id"],)).fetchone()
    assert row == {"is_active": False}


def test_report_and_evaluation_read_the_findings(db: Database, condominium: dict[str, Any], world: Any) -> None:
    store = MemoryStore()
    doc_id = _march(db, condominium, store, world)
    _processor(db, store).handle(process_message(condominium["id"], doc_id))
    AuditRunner(db).run(condominium["id"])

    report = render_report(db, condominium["slug"])
    detected = load_findings(db, [condominium["slug"]])

    assert "R$ 1.200,00 unaccounted for in the running balance" in report
    assert "Balancete" not in report or "page 1" in report
    assert ("BALANCE_CHAIN_BREAK", "2025-03") in {(f.rule_code, f.period) for f in detected}
