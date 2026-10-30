"""Wires job types to their handlers."""

from __future__ import annotations

from collections.abc import Mapping

from condo_audit.audit.runner import AuditRunner
from condo_audit.db import Database
from condo_audit.documents.reader import DocumentReader, TesseractEngine
from condo_audit.jobs import JobType
from condo_audit.processing import DocumentProcessor
from condo_audit.settings import Settings
from condo_audit.storage import DocumentStore
from condo_audit.worker import JobHandler


def build_handlers(db: Database, store: DocumentStore, settings: Settings) -> Mapping[JobType, JobHandler]:
    reader = DocumentReader(TesseractEngine(settings.ocr_language), dpi=settings.ocr_dpi)
    return {
        JobType.DOCUMENT_PROCESS: DocumentProcessor(db, store, reader).handle,
        JobType.AUDIT_RUN: AuditRunner(db).handle,
    }
