"""Integration tests run against the migrated test database
(`make test-pipeline` migrates it through the API before running pytest)."""

from __future__ import annotations

import os
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any

import pytest

from condo_audit.db import Database
from condo_audit.jobs import JobMessage, JobType


class MemoryStore:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    def get(self, key: str) -> bytes:
        return self.objects[key]


@pytest.fixture(scope="session")
def db() -> Iterator[Database]:
    url = os.environ.get("DATABASE_URL", "")
    if "condo_audit_test" not in url:
        pytest.skip("integration tests need DATABASE_URL pointing at condo_audit_test")
    database = Database(url)
    with database.transaction() as conn:
        if conn.execute("select to_regclass('public.findings') as t").fetchone()["t"] is None:  # type: ignore[index]
            pytest.skip("test database is not migrated (run `make test-pipeline`)")
    yield database
    database.close()


@pytest.fixture
def condominium(db: Database) -> Iterator[dict[str, Any]]:
    slug = f"it-{uuid.uuid4().hex[:8]}"
    with db.transaction() as conn:
        row = conn.execute(
            """
            insert into condominiums (name, slug, tax_id, settings, created_at, updated_at)
            values ('Condomínio Residencial Jardim das Acácias', %s, %s, '{}', now(), now()) returning id, slug, tax_id
            """,
            (slug, "00.000.000/0001-00"),
        ).fetchone()
    assert row is not None
    yield row
    with db.transaction() as conn:
        conn.execute("delete from pipeline_runs where condominium_id = %s", (row["id"],))
        conn.execute("delete from condominiums where id = %s", (row["id"],))


def add_document(db: Database, condominium_id: int, doc_type: str, key: str, period: str | None = None) -> int:
    with db.transaction() as conn:
        row = conn.execute(
            """
            insert into documents (condominium_id, type, title, reference_period, original_filename, storage_key,
                mime_type, size_bytes, sha256, status, ingested_at, metadata, created_at, updated_at)
            values (%s, %s, %s, %s, 'f.pdf', %s, 'application/pdf', 1, %s, 'pending', now(), '{}', now(), now())
            returning id
            """,
            (condominium_id, doc_type, key, period, key, uuid.uuid4().hex + uuid.uuid4().hex),
        ).fetchone()
    assert row is not None
    return int(row["id"])


def process_message(condominium_id: int, document_id: int) -> JobMessage:
    return JobMessage(
        schema_version=1,
        job_id=uuid.uuid4(),
        type=JobType.DOCUMENT_PROCESS,
        condominium_id=condominium_id,
        correlation_id="integration-test",
        enqueued_at=datetime.now(UTC),
        attempt=0,
        payload={"document_id": document_id},
    )
