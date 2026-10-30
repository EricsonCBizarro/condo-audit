from __future__ import annotations

from datetime import date
from decimal import Decimal

from condo_audit.extraction import governance as gov
from tests.helpers import page_from_lines


def test_budget_lines_map_to_categories_and_skip_totals() -> None:
    page = page_from_lines(
        [
            "PREVISÃO ORÇAMENTÁRIA 2025",
            "Categoria Valor mensal (R$)",
            "Energia elétrica 2.100,00",
            "Água e esgoto 3.600,00",
            "Total mensal 5.700,00",
        ]
    )
    year, lines = gov.parse_budget([page])
    assert year == 2025
    assert [(b.category, b.monthly_amount) for b in lines] == [
        ("energia", Decimal("2100.00")),
        ("agua", Decimal("3600.00")),
    ]


def test_meeting_notice_agenda() -> None:
    page = page_from_lines(
        [
            "Ficam convocados os condôminos no dia 14/08/2025, às 19h30, para deliberar:",
            "1. Troca do portão eletrônico da garagem;",
            "2. Regras de uso do salão de festas;",
        ]
    )
    when, items = gov.parse_meeting_notice([page])
    assert when == date(2025, 8, 14)
    assert [(i.number, i.subject) for i in items] == [
        (1, "Troca do portão eletrônico da garagem"),
        (2, "Regras de uso do salão de festas"),
    ]


def test_minutes_decisions_detect_approval_rejection_and_amount() -> None:
    page = page_from_lines(
        [
            "Aos 20 de março de 2025 (20/03/2025), reuniram-se os condôminos.",
            "Item 1 – Pintura da fachada. Deliberação: aprovada a contratação no valor total de",
            "R$ 48.000,00, em duas parcelas.",
            "Item 2 – Troca do portão. Deliberação: não aprovada, com 9 votos contrários.",
            "Nada mais havendo a tratar, foi encerrada a assembleia.",
        ]
    )
    when, decisions = gov.parse_meeting_minutes([page])
    assert when == date(2025, 3, 20)
    assert [(d.number, d.approved, d.amount) for d in decisions] == [
        (1, True, Decimal("48000.00")),
        (2, False, None),
    ]


def test_bylaws_clauses_and_penalty_ladder() -> None:
    page = page_from_lines(
        [
            "CAPÍTULO 8 — DAS PENALIDADES",
            "8.1 - As infrações serão punidas com a seguinte gradação: a) advertência por escrito, na",
            "primeira ocorrência; b) multa de 50% na segunda ocorrência; c) multa em dobro a partir da terceira.",
            "8.2 - A reincidência é contada por unidade.",
        ]
    )
    clauses, params = gov.parse_bylaws([page])
    assert [c.number for c in clauses] == ["8.1", "8.2"]
    assert params[0].key == "penalty_ladder"
    assert params[0].value["steps"] == ["warning", "fine", "fine"]


def test_convention_spending_limit_keeps_the_legal_text() -> None:
    page = page_from_lines(
        [
            "Art. 18 — O síndico poderá realizar despesas extraordinárias até o limite de R$ 5.000,00",
            "(cinco mil reais) por despesa, sem prévia aprovação da assembleia geral.",
        ]
    )
    [param] = gov.parse_convention([page])
    assert param.value == {"amount": "5000.00"}
    assert param.excerpt.startswith("Art. 18")


def test_penalty_notice() -> None:
    page = page_from_lines(
        [
            "NOTIFICAÇÃO DE INFRAÇÃO AO REGIMENTO INTERNO",
            "Unidade: B-12",
            "Data: 15/04/2025",
            "Infração: Animal de estimação solto em área comum",
            "Penalidade aplicada: MULTA",
            "Valor: R$ 475,00",
        ]
    )
    p = gov.parse_penalty_notice([page])
    assert p is not None
    assert (p.unit, p.kind, p.amount, p.issued_on) == ("B-12", "fine", Decimal("475.00"), date(2025, 4, 15))
