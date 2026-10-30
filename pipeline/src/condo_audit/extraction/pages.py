"""Page type classification by token co-occurrence (tolerant to OCR noise:
pairs of short stems instead of exact phrases)."""

from __future__ import annotations

from enum import StrEnum

from condo_audit.documents.layout import PageLayout
from condo_audit.extraction.text import DATE_RE, normalize


class PageType(StrEnum):
    STATEMENT = "statement"
    RECEIPT = "receipt"
    CONTRACT = "contract"
    OTHER = "other"


def classify_page(page: PageLayout) -> PageType:
    text = normalize(page.text)

    def both(a: str, b: str) -> bool:
        return a in text and b in text

    if "CLAUSULA" in text or both("CONTRATANTE", "CONTRATADA"):
        return PageType.CONTRACT
    if "COMPROVANTE" in text or "RECIBO" in text or both("AUTENTICA", "FAVORECIDO"):
        return PageType.RECEIPT
    dated_lines = sum(1 for line in page.lines if DATE_RE.match(line.text.strip()))
    if (both("SALDO", "ANTER") or both("EXTRATO", "CONTA")) and dated_lines >= 2:
        return PageType.STATEMENT
    return PageType.OTHER
