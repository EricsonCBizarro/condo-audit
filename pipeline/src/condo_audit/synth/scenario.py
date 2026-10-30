"""The fictional world: two invented condominiums over one year.

`with_irregularities` gets ten problems planted on purpose (each recorded as a
GroundTruthItem); `control` is clean and measures false positives. Every
name, number and company below is invented.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal

from condo_audit.formatting import money
from condo_audit.synth.taxid import fake_cnpj

YEAR = 2025
D = Decimal


@dataclass(frozen=True)
class Payee:
    name: str  # as printed on receipts
    label: str  # as printed on bank statements (upper case, no accents)
    category: str
    tax_id: str


@dataclass(frozen=True)
class ReceiptSpec:
    payee: str
    payer_name: str
    payer_tax_id: str
    amount: Decimal
    paid_on: date
    description: str


@dataclass
class Transaction:
    day: date
    description: str
    amount: Decimal  # signed: credits > 0, debits < 0
    receipt: ReceiptSpec | None = None


@dataclass
class MonthStatement:
    period: date
    opening: Decimal
    transactions: list[Transaction]
    printed_balances: list[Decimal] = field(default_factory=list)
    scanned: bool = False

    @property
    def closing(self) -> Decimal:
        return self.printed_balances[-1] if self.printed_balances else self.opening


@dataclass(frozen=True)
class Decision:
    item_number: int
    subject: str
    text: str


@dataclass
class Meeting:
    kind: str  # "ORDINÁRIA" | "EXTRAORDINÁRIA"
    held_on: date
    notice_on: date
    agenda: list[str]
    decisions: list[Decision]


@dataclass(frozen=True)
class PenaltySpec:
    unit: str
    resident: str
    infraction: str
    kind: str  # "ADVERTÊNCIA" | "MULTA"
    amount: Decimal | None
    issued_on: date


@dataclass(frozen=True)
class GroundTruthItem:
    rule_code: str
    period: str
    amount: Decimal | None
    note: str


@dataclass
class CondoSpec:
    slug: str
    name: str
    tax_id: str
    city: str
    address: str
    manager: str
    administrator: str
    units: list[str]
    monthly_fee: Decimal
    spending_limit: Decimal
    budget: dict[str, tuple[str, Decimal]]  # category -> (display name, monthly amount)
    statements: list[MonthStatement] = field(default_factory=list)
    meetings: list[Meeting] = field(default_factory=list)
    penalties: list[PenaltySpec] = field(default_factory=list)
    scanned: set[str] = field(default_factory=set)
    expected: list[GroundTruthItem] = field(default_factory=list)


# Names checked to be absent from any real document the project ever used.
FIRST_NAMES = [
    "Otávio",
    "Marina",
    "Lívia",
    "Luana",
    "Bruno",
    "Sofia",
    "Diego",
    "Murilo",
    "Heitor",
    "Yasmin",
    "Lorena",
    "Ítalo",
]
LAST_NAMES = [
    "Duarte",
    "Moreira",
    "Paixão",
    "Siqueira",
    "Fontana",
    "Brandão",
    "Cordeiro",
    "Quintela",
    "Arantes",
    "Bittencourt",
    "Lacerda",
    "Pacheco",
    "Falcão",
    "Vasconcelos",
]


def _person(rng: random.Random) -> str:
    return f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}"


def _units(blocks: str, floors: int, per_floor: int) -> list[str]:
    # Block-floor-unit codes (A-11, A-12, ...), never bare apartment numbers.
    return [f"{b}-{f}{u}" for b in blocks for f in range(1, floors + 1) for u in range(1, per_floor + 1)]


def _payees(rng: random.Random) -> dict[str, Payee]:
    def p(name: str, label: str, category: str) -> Payee:
        return Payee(name, label, category, fake_cnpj(rng))

    return {
        "administracao": p("Veredas Gestão Condominial Ltda.", "VEREDAS GESTAO CONDOMINIAL", "administracao"),
        "limpeza": p("Limpa Bem Serviços Ltda.", "LIMPA BEM SERVICOS", "limpeza"),
        "energia": p("Companhia Energética Aurora", "CIA ENERGETICA AURORA", "energia"),
        "agua": p("Águas do Vale Saneamento S.A.", "AGUAS DO VALE SANEAMENTO", "agua"),
        "manutencao": p("Elevadores Ascende Ltda.", "ELEVADORES ASCENDE", "manutencao"),
        "jardinagem": p("Jardins & Cia Paisagismo", "JARDINS E CIA PAISAGISMO", "jardinagem"),
        "seguranca": p("Atalaia Vigilância Eletrônica", "ATALAIA VIGILANCIA", "seguranca"),
        "seguro": p("Seguradora Horizonte S.A.", "SEGURADORA HORIZONTE", "seguro"),
        "pintura": p("Tintas & Reformas Alvorada Ltda.", "TINTAS E REFORMAS ALVORADA", "obras"),
        "serralheria": p("Serralheria Ponto Forte", "SERRALHERIA PONTO FORTE", "obras"),
        "telhado": p("Telhados Bom Abrigo Ltda.", "TELHADOS BOM ABRIGO", "obras"),
        "reparos": p("JM Reparos Gerais", "JM REPAROS GERAIS", "outros"),
    }


def month_end(period: date) -> date:
    nxt = date(period.year + period.month // 12, period.month % 12 + 1, 1)
    return nxt - timedelta(days=1)


class _LedgerBuilder:
    """Builds one condominium's monthly transactions with receipts."""

    def __init__(self, condo: CondoSpec, payees: dict[str, Payee], rng: random.Random, zelador: str) -> None:
        self.condo = condo
        self.payees = payees
        self.rng = rng
        self.zelador = zelador

    def receipt(self, payee: str, amount: Decimal, paid_on: date, description: str) -> ReceiptSpec:
        return ReceiptSpec(payee, self.condo.name, self.condo.tax_id, money(amount), paid_on, description)

    def pay(self, key: str, day: date, amount: Decimal, what: str, note: str = "") -> Transaction:
        payee = self.payees[key]
        text = f"PAGTO {what} - {payee.label}" if what else f"PAGTO {payee.label}"
        return Transaction(day, text, -money(amount), self.receipt(payee.name, amount, day, note or what.capitalize()))

    def regular_month(self, period: date) -> list[Transaction]:
        c, rng, month = self.condo, self.rng, period.month
        ref = f"ref. {month:02d}/{period.year}"
        units = len(c.units)
        on_time = int(units * 0.8)
        txs = [
            Transaction(period.replace(day=5), "TED RECEBIDA - TAXAS CONDOMINIAIS", money(c.monthly_fee * on_time)),
            Transaction(
                period.replace(day=12),
                "TED RECEBIDA - TAXAS CONDOMINIAIS",
                money(c.monthly_fee * (units - on_time - rng.randint(0, 2))),
            ),
            Transaction(period.replace(day=5), "CREDITO FUNDO DE OBRAS", money(D(200) * units)),
            self.pay(
                "administracao",
                period.replace(day=6),
                c.budget["administracao"][1],
                "TAXA DE ADMINISTRACAO",
                f"Taxa de administração {ref}",
            ),
            Transaction(
                period.replace(day=6),
                "PAGTO SALARIO ZELADOR",
                -c.budget["pessoal"][1],
                self.receipt(self.zelador, c.budget["pessoal"][1], period.replace(day=6), f"Salário {ref}"),
            ),
            self.pay(
                "energia",
                period.replace(day=8),
                c.budget["energia"][1] * D(rng.uniform(0.9, 1.04)).quantize(D("0.0001")),
                "ENERGIA",
                f"Fatura de energia elétrica {ref}",
            ),
            self.pay(
                "agua",
                period.replace(day=10),
                c.budget["agua"][1] * D(rng.uniform(0.9, 0.98)).quantize(D("0.0001")),
                "AGUA",
                f"Fatura de água e esgoto {ref}",
            ),
            self.pay(
                "manutencao",
                period.replace(day=7),
                c.budget["manutencao"][1],
                "MANUTENCAO ELEVADOR",
                f"Manutenção preventiva de elevadores {ref}",
            ),
            self.pay(
                "limpeza",
                period.replace(day=15),
                c.budget["limpeza"][1],
                "LIMPEZA",
                f"Serviços de limpeza {ref}",
            ),
            self.pay(
                "jardinagem",
                period.replace(day=20),
                c.budget["jardinagem"][1],
                "JARDINAGEM",
                f"Manutenção de jardins {ref}",
            ),
            self.pay(
                "seguranca",
                period.replace(day=25),
                c.budget["seguranca"][1],
                "MONITORAMENTO",
                f"Vigilância eletrônica {ref}",
            ),
            Transaction(period.replace(day=28), "RENDIMENTO APLICACAO", money(D(rng.uniform(40, 90)))),
            Transaction(period.replace(day=28), "TARIFA BANCARIA PACOTE SERVICOS", -D("58.90")),
        ]
        if month in (1, 4, 7, 10):
            premium = c.budget["seguro"][1] * 3
            txs.append(
                self.pay("seguro", period.replace(day=18), premium, "SEGURO PREDIAL", "Seguro predial trimestral")
            )
        return txs


def _finalize(condo: CondoSpec, months: dict[int, list[Transaction]], opening: Decimal) -> None:
    """Sort, compute printed balances and chain the months."""
    balance = opening
    for month in range(1, 13):
        txs = sorted(months[month], key=lambda t: (t.day, t.amount < 0))
        statement = MonthStatement(date(YEAR, month, 1), balance, txs)
        running = balance
        for tx in txs:
            running += tx.amount
            statement.printed_balances.append(running)
        condo.statements.append(statement)
        balance = running


def _build_irregular(rng: random.Random) -> CondoSpec:
    condo = CondoSpec(
        slug="residencial-jardim-das-acacias",
        name="Condomínio Residencial Jardim das Acácias",
        tax_id=fake_cnpj(rng),
        city="Vale Sereno",
        address="Rua das Hortênsias, 1180 - Bairro Bela Vista - Vale Sereno",
        manager=_person(rng),
        administrator="Veredas Gestão Condominial Ltda.",
        units=_units("AB", 3, 4),
        monthly_fee=D("950.00"),
        spending_limit=D("5000.00"),
        budget={
            "administracao": ("Taxa de administração", D("1900.00")),
            "pessoal": ("Pessoal (salários e encargos)", D("3800.00")),
            "limpeza": ("Limpeza", D("4380.00")),
            "energia": ("Energia elétrica", D("2100.00")),
            "agua": ("Água e esgoto", D("3600.00")),
            "manutencao": ("Manutenção de elevadores", D("1200.00")),
            "jardinagem": ("Jardinagem", D("600.00")),
            "seguranca": ("Segurança e monitoramento", D("3200.00")),
            "seguro": ("Seguro predial", D("800.00")),
            "outros": ("Despesas diversas", D("500.00")),
            "tarifas_bancarias": ("Tarifas bancárias", D("60.00")),
        },
        scanned={"financial_statement:2025-02", "financial_statement:2025-10", "bylaws"},
    )
    payees = _payees(rng)
    b = _LedgerBuilder(condo, payees, rng, zelador=_person(rng))
    months = {m: b.regular_month(date(YEAR, m, 1)) for m in range(1, 13)}
    gt = condo.expected

    # Gardening is billed above budget all year long.
    for m in range(1, 13):
        for tx in months[m]:
            if "JARDINAGEM" in tx.description:
                tx.amount = -D("950.00")
                tx.receipt = b.receipt(payees["jardinagem"].name, D("950.00"), tx.day, "Manutenção de jardins")
    gt.append(GroundTruthItem("BUDGET_OVERRUN", "2025", D("4200.00"), "Gardening: 950/month vs 600 budgeted"))

    # Approved facade painting (control: must NOT be flagged), two installments.
    for m, n in ((5, 1), (6, 2)):
        months[m].append(
            b.pay(
                "pintura",
                date(YEAR, m, 16),
                D("24000.00"),
                f"PINTURA FACHADA PARC {n}/2",
                f"Pintura da fachada, parcela {n}/2",
            )
        )

    # April: a debit with no receipt at all.
    months[4].append(Transaction(date(YEAR, 4, 22), "PAGTO SERVICOS DIVERSOS - JM REPAROS GERAIS", -D("2800.00")))
    gt.append(GroundTruthItem("MISSING_RECEIPT", "2025-04", D("2800.00"), "No receipt for JM Reparos"))

    # May: the cleaning receipt says 3.840,00 but 4.380,00 left the account.
    for tx in months[5]:
        if "LIMPEZA" in tx.description:
            tx.receipt = b.receipt(payees["limpeza"].name, D("3840.00"), tx.day, "Serviços de limpeza")
    gt.append(GroundTruthItem("RECEIPT_AMOUNT_MISMATCH", "2025-05", D("540.00"), "Paid 4380, receipt 3840"))

    # July: elevator maintenance paid twice, three days apart.
    months[7].append(
        b.pay("manutencao", date(YEAR, 7, 10), D("1200.00"), "MANUTENCAO ELEVADOR", "Manutenção de elevadores")
    )
    gt.append(GroundTruthItem("DUPLICATE_PAYMENT", "2025-07", D("1200.00"), "Elevator paid on 07/07 and 10/07"))

    # August: a water bill that belongs to another condominium.
    other = "Condomínio Edifício Solar das Palmeiras"
    months[8].append(
        Transaction(
            date(YEAR, 8, 19),
            "PAGTO BOLETO - AGUAS DO VALE SANEAMENTO",
            -D("1870.40"),
            ReceiptSpec(
                payees["agua"].name,
                other,
                fake_cnpj(rng),
                D("1870.40"),
                date(YEAR, 8, 19),
                "Fatura de água e esgoto",
            ),
        )
    )
    gt.append(GroundTruthItem("FOREIGN_DOCUMENT", "2025-08", D("1870.40"), f"Receipt issued to {other}"))

    # October (scanned statement): gate replacement rejected by the assembly, paid anyway.
    months[10].append(
        b.pay(
            "serralheria",
            date(YEAR, 10, 9),
            D("9700.00"),
            "TROCA PORTAO ELETRONICO",
            "Troca do portão eletrônico da garagem",
        )
    )
    gt.append(GroundTruthItem("UNAPPROVED_EXPENSE", "2025-10", D("9700.00"), "Gate rejected in the August AGE"))

    _finalize(condo, months, opening=D("31250.75"))

    # March: 1.200,00 disappears inside the statement (printed balance jumps).
    march = condo.statements[2]
    idx = next(i for i, t in enumerate(march.transactions) if "AGUA" in t.description)
    for i in range(idx, len(march.printed_balances)):
        march.printed_balances[i] -= D("1200.00")
    gt.append(GroundTruthItem("BALANCE_CHAIN_BREAK", "2025-03", D("1200.00"), "Balance drops 1200 after water bill"))
    _rechain(condo, start=3)

    # September opens 3.450,00 below August's closing balance.
    condo.statements[8].opening -= D("3450.00")
    _recompute(condo.statements[8])
    gt.append(
        GroundTruthItem("OPENING_BALANCE_MISMATCH", "2025-09", D("3450.00"), "September opening ≠ August closing")
    )
    _rechain(condo, start=9)

    condo.meetings = [
        Meeting(
            "ORDINÁRIA",
            date(YEAR, 3, 20),
            date(YEAR, 3, 5),
            [
                "Prestação de contas do exercício de 2024",
                "Aprovação da previsão orçamentária de 2025",
                "Pintura da fachada (orçamento de R$ 48.000,00)",
                "Eleição do síndico para o biênio 2025-2026",
            ],
            [
                Decision(1, "Prestação de contas do exercício de 2024", "aprovada por unanimidade."),
                Decision(2, "Aprovação da previsão orçamentária de 2025", "aprovada por maioria."),
                Decision(
                    3,
                    "Pintura da fachada",
                    "aprovada a contratação da empresa Tintas & Reformas Alvorada Ltda., no valor total "
                    "de R$ 48.000,00, pago em duas parcelas.",
                ),
                Decision(4, "Eleição do síndico", f"eleito(a) {condo.manager} por aclamação."),
            ],
        ),
        Meeting(
            "EXTRAORDINÁRIA",
            date(YEAR, 8, 14),
            date(YEAR, 7, 30),
            [
                "Troca do portão eletrônico da garagem",
                "Regras de uso do salão de festas",
                "Assuntos gerais",
            ],
            [
                Decision(
                    1,
                    "Troca do portão eletrônico da garagem",
                    "não aprovada, com 9 votos contrários e 5 favoráveis. O portão atual será apenas revisado.",
                ),
                # Item 2 is never deliberated (planted).
                Decision(3, "Assuntos gerais", "os presentes pediram a revisão das luminárias do hall."),
            ],
        ),
    ]
    gt.append(GroundTruthItem("AGENDA_ITEM_NOT_DELIBERATED", "2025-08", None, "Item 2 missing in the AGE minutes"))

    condo.penalties = [
        PenaltySpec("A-21", _person(rng), "Ruído excessivo após as 22h", "ADVERTÊNCIA", None, date(YEAR, 2, 10)),
        PenaltySpec("A-21", _person(rng), "Ruído excessivo após as 22h", "MULTA", D("475.00"), date(YEAR, 6, 3)),
        PenaltySpec(
            "B-12",
            _person(rng),
            "Animal de estimação solto em área comum",
            "MULTA",
            D("475.00"),
            date(YEAR, 4, 15),
        ),
    ]
    gt.append(GroundTruthItem("PENALTY_LADDER_VIOLATION", "2025-04", D("475.00"), "Fine on first occurrence (B-12)"))
    return condo


def _build_control(rng: random.Random) -> CondoSpec:
    condo = CondoSpec(
        slug="edificio-mirante-do-vale",
        name="Condomínio Edifício Mirante do Vale",
        tax_id=fake_cnpj(rng),
        city="Porto Claro",
        address="Avenida dos Ipês, 455 - Centro - Porto Claro",
        manager=_person(rng),
        administrator="Veredas Gestão Condominial Ltda.",
        units=_units("A", 4, 4),
        monthly_fee=D("780.00"),
        spending_limit=D("8000.00"),
        budget={
            "administracao": ("Taxa de administração", D("1500.00")),
            "pessoal": ("Pessoal (salários e encargos)", D("3100.00")),
            "limpeza": ("Limpeza", D("2600.00")),
            "energia": ("Energia elétrica", D("1500.00")),
            "agua": ("Água e esgoto", D("2400.00")),
            "manutencao": ("Manutenção de elevadores", D("950.00")),
            "jardinagem": ("Jardinagem", D("350.00")),
            "seguranca": ("Segurança e monitoramento", D("1900.00")),
            "seguro": ("Seguro predial", D("600.00")),
            "outros": ("Despesas diversas", D("400.00")),
            "tarifas_bancarias": ("Tarifas bancárias", D("60.00")),
        },
        scanned={"financial_statement:2025-03", "financial_statement:2025-09", "convention"},
    )
    payees = _payees(rng)
    b = _LedgerBuilder(condo, payees, rng, zelador=_person(rng))
    months = {m: b.regular_month(date(YEAR, m, 1)) for m in range(1, 13)}
    # Approved roof repair above the spending limit (control: must NOT be flagged).
    months[9].append(
        b.pay("telhado", date(YEAR, 9, 11), D("12000.00"), "REFORMA TELHADO", "Reforma do telhado do bloco A")
    )
    _finalize(condo, months, opening=D("18740.20"))
    condo.meetings = [
        Meeting(
            "ORDINÁRIA",
            date(YEAR, 4, 10),
            date(YEAR, 3, 26),
            [
                "Prestação de contas do exercício de 2024",
                "Aprovação da previsão orçamentária de 2025",
                "Reforma do telhado do bloco A (orçamento de R$ 12.000,00)",
            ],
            [
                Decision(1, "Prestação de contas do exercício de 2024", "aprovada por unanimidade."),
                Decision(2, "Aprovação da previsão orçamentária de 2025", "aprovada por unanimidade."),
                Decision(
                    3,
                    "Reforma do telhado do bloco A",
                    "aprovada a contratação da empresa Telhados Bom Abrigo Ltda., no valor de R$ 12.000,00.",
                ),
            ],
        )
    ]
    condo.penalties = [
        PenaltySpec("A-32", _person(rng), "Uso indevido da garagem", "ADVERTÊNCIA", None, date(YEAR, 5, 8)),
    ]
    return condo


def _recompute(statement: MonthStatement) -> None:
    running = statement.opening
    statement.printed_balances = []
    for tx in statement.transactions:
        running += tx.amount
        statement.printed_balances.append(running)


def _rechain(condo: CondoSpec, start: int) -> None:
    """Months after `start` open with the previous printed closing."""
    for i in range(start, len(condo.statements)):
        condo.statements[i].opening = condo.statements[i - 1].closing
        _recompute(condo.statements[i])


def build_world(seed: int = 42) -> list[CondoSpec]:
    rng = random.Random(seed)
    return [_build_irregular(rng), _build_control(rng)]
