"""Expense categories by keyword. Order matters: first match wins.

Operators can override the keywords per condominium (settings.category_keywords).
This deterministic classifier is the baseline the AI phase will be measured against.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from condo_audit.extraction.text import normalize

DEFAULT_KEYWORDS: dict[str, tuple[str, ...]] = {
    "tarifas_bancarias": ("TARIFA",),
    "administracao": ("ADMINISTRACAO", "GESTAO CONDOMINIAL"),
    "pessoal": ("SALARIO", "FOLHA", "PESSOAL", "INSS", "FGTS"),
    "limpeza": ("LIMPEZA", "LIMPA BEM"),
    "energia": ("ENERGIA", "ENERGETICA"),
    "agua": ("AGUA", "SANEAMENTO"),
    "manutencao": ("ELEVADOR", "MANUTENCAO"),
    "jardinagem": ("JARDIN", "PAISAGISMO"),
    "seguranca": ("VIGILANCIA", "SEGURANCA", "MONITORAMENTO", "PORTARIA"),
    "seguro": ("SEGURO", "SEGURADORA"),
    "obras": ("OBRA", "REFORMA", "PINTURA", "SERRALHERIA", "TELHADO", "PORTAO"),
    "outros": ("DIVERS",),
}


def categorize(description: str, keywords: Mapping[str, Sequence[str]] | None = None) -> str | None:
    text = normalize(description)
    for category, words in (keywords or DEFAULT_KEYWORDS).items():
        if any(word in text for word in words):
            return category
    return None
