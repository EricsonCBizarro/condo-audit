from __future__ import annotations

import random
import shutil

import pytest

from condo_audit.documents.reader import DocumentReader, TesseractEngine
from condo_audit.extraction.pages import PageType, classify_page
from condo_audit.extraction.statement import Reconciliation, parse_rows
from condo_audit.synth import render
from condo_audit.synth.scan import scanned
from condo_audit.synth.scenario import build_world

pytestmark = [
    pytest.mark.ocr,
    pytest.mark.skipif(shutil.which("tesseract") is None, reason="tesseract binary not installed"),
]


def test_a_scanned_statement_is_read_by_ocr_and_reconciles() -> None:
    condo = build_world(42)[1]  # control condominium: every month reconciles
    pdf = scanned(render.financial_statement(condo, condo.statements[0]), random.Random(1))

    pages = list(DocumentReader(TesseractEngine()).pages(pdf))
    statement_pages = [p for p in pages if classify_page(p) is PageType.STATEMENT]
    rows = parse_rows(statement_pages)

    assert all(p.source == "ocr" for p in pages)
    assert len(rows) == len(condo.statements[0].transactions) + 2  # + opening and closing
    assert {r.reconciliation for r in rows} == {Reconciliation.OK}
