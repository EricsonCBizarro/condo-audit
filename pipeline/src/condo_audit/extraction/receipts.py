"""Payment receipts attached to the monthly statement."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from condo_audit.documents.layout import PageLayout
from condo_audit.extraction.fields import labeled_fields
from condo_audit.extraction.money import parse_brl
from condo_audit.extraction.text import parse_date


@dataclass(frozen=True, slots=True)
class ReceiptData:
    page: int
    payee: str | None
    payer_name: str | None
    payer_tax_id: str | None
    amount: Decimal | None
    paid_on: date | None
    description: str | None
    confidence: float


def parse_receipt(page: PageLayout) -> ReceiptData:
    f = labeled_fields(page)

    def get(*labels: str) -> str | None:
        for label in labels:
            if label in f:
                return f[label][0]
        return None

    amount = get("VALOR", "VALOR PAGO", "VALOR TOTAL")
    paid_on = get("DATA DO PAGAMENTO", "DATA", "PAGO EM")
    return ReceiptData(
        page=page.number,
        payee=get("FAVORECIDO", "BENEFICIARIO", "RECEBEDOR"),
        payer_name=get("PAGADOR", "SACADO"),
        payer_tax_id=get("CNPJ DO PAGADOR", "CNPJ"),
        amount=parse_brl(amount) if amount else None,
        paid_on=parse_date(paid_on) if paid_on else None,
        description=get("DESCRICAO", "HISTORICO", "REFERENCIA"),
        confidence=page.mean_confidence,
    )
