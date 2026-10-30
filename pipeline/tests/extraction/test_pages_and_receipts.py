from __future__ import annotations

from datetime import date
from decimal import Decimal

from condo_audit.extraction.pages import PageType, classify_page
from condo_audit.extraction.receipts import parse_receipt
from tests.helpers import page_from_lines

RECEIPT = [
    "COMPROVANTE DE PAGAMENTO",
    "Pagador: Condomínio Exemplo",
    "CNPJ do pagador: 12.345.678/0001-00",
    "Favorecido: Limpa Bem Serviços Ltda.",
    "Data do pagamento: 15/05/2025",
    "Valor: R$ 3.840,00",
    "Descrição: Serviços de limpeza",
]


def test_page_classification() -> None:
    statement = ["EXTRATO DA CONTA CORRENTE", "01/03/2025 SALDO ANTERIOR 1,00", "02/03/2025 X 1,00 2,00"]
    assert classify_page(page_from_lines(statement)) is PageType.STATEMENT
    assert classify_page(page_from_lines(RECEIPT)) is PageType.RECEIPT
    assert classify_page(page_from_lines(["CLÁUSULA PRIMEIRA - DO OBJETO"])) is PageType.CONTRACT
    assert classify_page(page_from_lines(["Comunicado aos moradores"])) is PageType.OTHER


def test_receipt_fields() -> None:
    r = parse_receipt(page_from_lines(RECEIPT, number=7))
    assert r.page == 7
    assert r.payee == "Limpa Bem Serviços Ltda."
    assert r.payer_name == "Condomínio Exemplo"
    assert r.payer_tax_id == "12.345.678/0001-00"
    assert r.amount == Decimal("3840.00")
    assert r.paid_on == date(2025, 5, 15)
