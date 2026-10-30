from __future__ import annotations

from datetime import date

import pytest

from condo_audit.extraction.categories import categorize
from condo_audit.extraction.text import clean_tokens, parse_date, significant_tokens


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("10/03/2025 PAGTO", date(2025, 3, 10)),
        ("Data: 1/2/25", date(2025, 2, 1)),
        ("31/02/2025", None),
        ("sem data", None),
    ],
)
def test_parse_date(text: str, expected: date | None) -> None:
    assert parse_date(text) == expected


def test_clean_tokens_drops_table_borders_read_by_ocr() -> None:
    assert clean_tokens("06/10/2025 | PAGTO || SALARIO") == "06/10/2025 PAGTO SALARIO"


def test_significant_tokens_ignore_accents_case_and_generic_words() -> None:
    assert significant_tokens("Pagto Manutenção do Elevador LTDA") == {"MANUTENCAO", "ELEVADOR"}


@pytest.mark.parametrize(
    ("description", "category"),
    [
        ("PAGTO SEGURO PREDIAL - SEGURADORA HORIZONTE", "seguro"),
        ("PAGTO MONITORAMENTO - ATALAIA VIGILANCIA", "seguranca"),
        ("Segurança e monitoramento", "seguranca"),
        ("PAGTO MANUTENCAO ELEVADOR - ELEVADORES ASCENDE", "manutencao"),
        ("Água e esgoto", "agua"),
        ("PAGTO TROCA PORTAO ELETRONICO - SERRALHERIA", "obras"),
        ("TARIFA BANCARIA PACOTE SERVICOS", "tarifas_bancarias"),
        ("TED RECEBIDA - TAXAS CONDOMINIAIS", None),
    ],
)
def test_categorize(description: str, category: str | None) -> None:
    assert categorize(description) == category


def test_categorize_accepts_per_condominium_keywords() -> None:
    assert categorize("PAGTO PISCINEIRO", {"piscina": ["PISCIN"]}) == "piscina"
