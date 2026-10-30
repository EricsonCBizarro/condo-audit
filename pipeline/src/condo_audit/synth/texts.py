"""Text of the governing documents (convention, bylaws, notices, minutes).

Written from scratch for the fictional world: generic clauses in the style of
Brazilian condominium documents, with the parameters the audit rules use
(spending limit, penalty ladder) stated the way real documents state them.
"""

from __future__ import annotations

from condo_audit.formatting import brl, d, long_date
from condo_audit.synth.scenario import CondoSpec, Meeting

Block = tuple[str, str]  # (style, text): style in {"title", "subtitle", "heading", "body"}

_NUMBER_WORDS = {
    "5000.00": "cinco mil reais",
    "8000.00": "oito mil reais",
}


def convention(condo: CondoSpec) -> list[Block]:
    limit = f"{condo.spending_limit:.2f}"
    return [
        ("title", f"CONVENÇÃO DO {condo.name.upper()}"),
        ("subtitle", f"CNPJ {condo.tax_id} — {condo.address}"),
        ("heading", "CAPÍTULO I — DO CONDOMÍNIO E SUAS PARTES"),
        (
            "body",
            "Art. 1º — O condomínio é constituído pelas unidades autônomas e pelas partes de uso comum, "
            "regendo-se por esta Convenção, pelo Regimento Interno e pela legislação aplicável.",
        ),
        (
            "body",
            f"Art. 2º — O condomínio é composto por {len(condo.units)} unidades autônomas, cada uma com "
            "fração ideal igual sobre o terreno e as partes comuns.",
        ),
        ("heading", "CAPÍTULO II — DAS DESPESAS E DA CONTRIBUIÇÃO"),
        (
            "body",
            "Art. 9º — Cada condômino contribuirá mensalmente para as despesas ordinárias na proporção de "
            "sua fração ideal, conforme a previsão orçamentária aprovada em assembleia.",
        ),
        (
            "body",
            "Art. 10 — O atraso no pagamento da contribuição sujeita o condômino a multa de 2% e juros "
            "de 1% ao mês sobre o valor devido.",
        ),
        ("heading", "CAPÍTULO III — DA ADMINISTRAÇÃO"),
        (
            "body",
            "Art. 16 — O condomínio será administrado por um síndico eleito em assembleia geral, para "
            "mandato de dois anos, permitida a reeleição.",
        ),
        (
            "body",
            "Art. 17 — Compete ao síndico prestar contas anualmente à assembleia e manter à disposição "
            "dos condôminos os balancetes mensais e seus comprovantes.",
        ),
        (
            "body",
            "Art. 18 — O síndico poderá realizar despesas extraordinárias até o limite de "
            f"R$ {brl(condo.spending_limit)} ({_NUMBER_WORDS.get(limit, 'valor por extenso')}) por despesa, "
            "sem prévia aprovação da assembleia geral. Despesas extraordinárias acima desse valor "
            "dependem de aprovação expressa em assembleia.",
        ),
        ("heading", "CAPÍTULO IV — DAS ASSEMBLEIAS"),
        (
            "body",
            "Art. 22 — A assembleia geral ordinária reunir-se-á anualmente para aprovar as contas e a "
            "previsão orçamentária. As assembleias extraordinárias serão convocadas com antecedência "
            "mínima de oito dias, mediante edital com a ordem do dia.",
        ),
        (
            "body",
            "Art. 23 — Toda matéria constante da ordem do dia deverá ser deliberada e registrada em ata.",
        ),
    ]


def bylaws(condo: CondoSpec) -> list[Block]:
    return [
        ("title", "REGIMENTO INTERNO"),
        ("subtitle", condo.name),
        ("heading", "CAPÍTULO 1 — DO SOSSEGO"),
        (
            "body",
            "1.1 - É proibido produzir ruídos que perturbem o sossego dos demais moradores entre as 22h e as 7h.",
        ),
        (
            "body",
            "1.2 - Obras e reformas nas unidades somente poderão ocorrer em dias úteis, das 8h às 18h, "
            "com aviso prévio à administração.",
        ),
        ("heading", "CAPÍTULO 2 — DAS ÁREAS COMUNS"),
        ("body", "2.1 - Animais de estimação devem circular nas áreas comuns sempre conduzidos por guia."),
        ("body", "2.2 - O salão de festas deve ser reservado com antecedência mínima de sete dias."),
        ("heading", "CAPÍTULO 3 — DA GARAGEM"),
        ("body", "3.1 - Cada unidade tem direito ao uso de uma vaga, sendo proibido o uso como depósito."),
        ("heading", "CAPÍTULO 8 — DAS PENALIDADES"),
        (
            "body",
            "8.1 - As infrações a este Regimento serão punidas com a seguinte gradação: "
            "a) advertência por escrito, na primeira ocorrência; "
            "b) multa de 50% (cinquenta por cento) da taxa condominial, na segunda ocorrência; "
            "c) multa de 100% (cem por cento) da taxa condominial, na terceira ocorrência; "
            "d) multa em dobro, a partir da quarta ocorrência.",
        ),
        (
            "body",
            "8.2 - A reincidência é contada por tipo de infração e por unidade, no período de doze meses.",
        ),
        (
            "body",
            "8.3 - O condômino poderá apresentar defesa por escrito no prazo de dez dias do recebimento "
            "da notificação.",
        ),
    ]


def meeting_notice(condo: CondoSpec, meeting: Meeting) -> list[Block]:
    items = [("body", f"{i}. {subject};") for i, subject in enumerate(meeting.agenda, start=1)]
    return [
        ("title", f"EDITAL DE CONVOCAÇÃO — ASSEMBLEIA GERAL {meeting.kind}"),
        ("subtitle", condo.name),
        (
            "body",
            f"Ficam convocados os senhores condôminos a se reunirem em assembleia geral {meeting.kind.lower()}, "
            f"no dia {d(meeting.held_on)}, às 19h30, no salão de festas do condomínio, em primeira "
            "convocação com a presença da maioria, ou às 20h em segunda convocação com qualquer número, "
            "para deliberar sobre a seguinte ordem do dia:",
        ),
        *items,
        ("body", f"{condo.city}, {long_date(meeting.notice_on)}."),
        ("body", f"{condo.manager} — Síndico(a)"),
    ]


def meeting_minutes(condo: CondoSpec, meeting: Meeting) -> list[Block]:
    decisions = [
        ("body", f"Item {dec.item_number} – {dec.subject}. Deliberação: {dec.text}") for dec in meeting.decisions
    ]
    return [
        ("title", f"ATA DA ASSEMBLEIA GERAL {meeting.kind} DO {condo.name.upper()}"),
        (
            "body",
            f"Aos {long_date(meeting.held_on)} ({d(meeting.held_on)}), às 20h, no salão de festas, reuniram-se "
            "em segunda convocação os condôminos que assinaram a lista de presença, sob a presidência de "
            f"{condo.manager}. Aberta a sessão, passou-se à ordem do dia constante do edital.",
        ),
        *decisions,
        (
            "body",
            "Nada mais havendo a tratar, foi encerrada a assembleia, lavrando-se a presente ata, que vai "
            "assinada pelo presidente e pelo secretário.",
        ),
    ]
