"""'Label: value' forms (receipts, penalty notices)."""

from __future__ import annotations

from condo_audit.documents.layout import PageLayout
from condo_audit.extraction.text import clean_tokens, normalize


def labeled_fields(page: PageLayout) -> dict[str, tuple[str, float]]:
    """{NORMALIZED LABEL: (value, line confidence)}; first occurrence wins."""
    fields: dict[str, tuple[str, float]] = {}
    for line in page.lines:
        text = clean_tokens(line.text)
        label, sep, value = text.partition(":")
        if not sep or not value.strip() or len(label) > 40:
            continue
        fields.setdefault(normalize(label), (value.strip(), line.confidence))
    return fields
