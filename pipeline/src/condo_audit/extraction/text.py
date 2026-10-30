"""Small text helpers shared by extractors."""

from __future__ import annotations

import re
import unicodedata
from datetime import date

DATE_RE = re.compile(r"(?<!\d)(\d{1,2})[/.](\d{1,2})[/.](\d{4}|\d{2})(?!\d)")
NOISE_TOKENS = {"|", "||", "¦", "—", "_"}
STOPWORDS = {
    "PAGTO",
    "PAGAMENTO",
    "SERVICOS",
    "LTDA",
    "PARC",
    "PARCELA",
    "FATURA",
    "REF",
    "BOLETO",
    "TOTAL",
    "VALOR",
    "EMPRESA",
    "CONTRATACAO",
    "APROVADA",
    "APROVADO",
    "PARA",
}


def strip_accents(value: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", value) if unicodedata.category(c) != "Mn")


def normalize(value: str) -> str:
    """Upper case, no accents, single spaces: the form keywords are matched against."""
    return " ".join(strip_accents(value).upper().split())


def clean_tokens(value: str) -> str:
    """Drop OCR artefacts such as table borders read as '|'."""
    return " ".join(t for t in value.split() if t not in NOISE_TOKENS)


def parse_date(value: str) -> date | None:
    match = DATE_RE.search(value)
    if not match:
        return None
    day, month, year = (int(g) for g in match.groups())
    if year < 100:
        year += 2000
    try:
        return date(year, month, day)
    except ValueError:
        return None


def significant_tokens(value: str, min_length: int = 5) -> set[str]:
    """Distinctive words, used to match descriptions across documents."""
    words = re.findall(r"[A-Z]+", normalize(value))
    return {w for w in words if len(w) >= min_length and w not in STOPWORDS}
