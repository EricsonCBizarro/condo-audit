"""PDF rendering with ReportLab. `invariant` mode makes output byte-for-byte
reproducible, so the same seed always yields the same SHA-256."""

from __future__ import annotations

import hashlib
import io
from datetime import timedelta
from decimal import Decimal

from reportlab import rl_config
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from condo_audit.formatting import brl, d
from condo_audit.synth.scenario import CondoSpec, MonthStatement, PenaltySpec, ReceiptSpec, month_end
from condo_audit.synth.texts import Block

rl_config.invariant = 1

WIDTH, HEIGHT = A4
LEFT = 48
ROW = 17
ROWS_PER_PAGE = 34
COL_DESC = LEFT + 66
COL_VALUE = WIDTH - 128  # right edge of the amount column
DESC_MAX_WIDTH = COL_VALUE - 72 - COL_DESC


def _fit(text: str, font: str, size: float, max_width: float) -> str:
    """Bank statements truncate long descriptions instead of wrapping."""
    while stringWidth(text, font, size) > max_width and len(text) > 4:
        text = text[:-1]
    return text.rstrip(" -")


AUTHOR = "condo-audit synthetic data"


def _canvas(buf: io.BytesIO, title: str) -> Canvas:
    c = Canvas(buf, pagesize=A4, invariant=1)
    c.setTitle(title)
    c.setAuthor(AUTHOR)
    return c


def text_document(title: str, blocks: list[Block]) -> bytes:
    buf = io.BytesIO()
    styles = getSampleStyleSheet()
    style_map = {
        "title": ParagraphStyle("t", parent=styles["Title"], fontSize=14, leading=18),
        "subtitle": ParagraphStyle("s", parent=styles["Normal"], alignment=1, fontSize=10, spaceAfter=12),
        "heading": ParagraphStyle("h", parent=styles["Heading3"], fontSize=11, spaceBefore=10),
        "body": ParagraphStyle("b", parent=styles["Normal"], fontSize=10.5, leading=15, spaceAfter=6),
    }
    doc = SimpleDocTemplate(buf, pagesize=A4, title=title, author=AUTHOR, leftMargin=56, rightMargin=56, invariant=1)
    story: list[Paragraph | Spacer] = []
    for style, text in blocks:
        story.append(Paragraph(text.replace("&", "&amp;"), style_map[style]))
    doc.build(story)
    return buf.getvalue()


def financial_statement(condo: CondoSpec, statement: MonthStatement) -> bytes:
    """Monthly statement: bank account extract followed by one receipt page
    per payment that has a receipt."""
    buf = io.BytesIO()
    period = statement.period
    c = _canvas(buf, f"Balancete {period:%m/%Y}")
    rows: list[tuple[str, str, str, str]] = [
        (d(period - timedelta(days=1)), "SALDO ANTERIOR", "", brl(statement.opening))
    ]
    for tx, balance in zip(statement.transactions, statement.printed_balances, strict=True):
        rows.append((d(tx.day), tx.description, brl(tx.amount), brl(balance)))
    rows.append((d(month_end(period)), "SALDO FINAL", "", brl(statement.closing)))

    chunks = [rows[i : i + ROWS_PER_PAGE] for i in range(0, len(rows), ROWS_PER_PAGE)]
    for page_index, chunk in enumerate(chunks):
        y = HEIGHT - 56
        if page_index == 0:
            c.setFont("Helvetica-Bold", 14)
            c.drawString(LEFT, y, "BALANCETE MENSAL")
            c.setFont("Helvetica", 10)
            for line in (
                condo.name,
                f"CNPJ: {condo.tax_id}",
                f"Administradora: {condo.administrator}",
                f"Período: {d(period)} a {d(month_end(period))}",
            ):
                y -= 15
                c.drawString(LEFT, y, line)
            y -= 26
        c.setFont("Helvetica-Bold", 11)
        c.drawString(LEFT, y, "EXTRATO DA CONTA CORRENTE" + (" (continuação)" if page_index else ""))
        y -= 20
        c.setFont("Helvetica-Bold", 9.5)
        c.drawString(LEFT, y, "Data")
        c.drawString(COL_DESC, y, "Histórico")
        c.drawRightString(COL_VALUE, y, "Valor (R$)")
        c.drawRightString(WIDTH - LEFT, y, "Saldo (R$)")
        c.setFont("Helvetica", 9.5)
        for date_s, desc, value, balance_s in chunk:
            y -= ROW
            c.drawString(LEFT, y, date_s)
            c.drawString(COL_DESC, y, _fit(desc, "Helvetica", 9.5, DESC_MAX_WIDTH))
            if value:
                c.drawRightString(COL_VALUE, y, value)
            c.drawRightString(WIDTH - LEFT, y, balance_s)
        c.setFont("Helvetica", 8)
        c.drawString(LEFT, 36, f"{condo.name} — balancete {period:%m/%Y}")
        c.showPage()

    for tx in statement.transactions:
        if tx.receipt is not None:
            _receipt_page(c, tx.receipt)
    c.save()
    return buf.getvalue()


def _receipt_page(c: Canvas, r: ReceiptSpec) -> None:
    auth = hashlib.sha256(f"{r.payee}|{r.amount}|{r.paid_on}|{r.payer_tax_id}".encode()).hexdigest()[:32]
    y = HEIGHT - 90
    c.setFont("Helvetica-Bold", 14)
    c.drawString(LEFT + 20, y, "COMPROVANTE DE PAGAMENTO")
    c.setFont("Helvetica", 11)
    fields = [
        ("Pagador", r.payer_name),
        ("CNPJ do pagador", r.payer_tax_id),
        ("Favorecido", r.payee),
        ("Data do pagamento", d(r.paid_on)),
        ("Valor", f"R$ {brl(r.amount)}"),
        ("Descrição", r.description),
        ("Autenticação", auth.upper()),
    ]
    y -= 30
    for label, value in fields:
        y -= 22
        c.drawString(LEFT + 20, y, f"{label}: {value}")
    c.rect(LEFT, y - 20, WIDTH - 2 * LEFT, HEIGHT - 90 - y + 50, stroke=1, fill=0)
    c.showPage()


def budget(condo: CondoSpec, approved_on: str) -> bytes:
    buf = io.BytesIO()
    c = _canvas(buf, "Previsão orçamentária 2025")
    y = HEIGHT - 60
    c.setFont("Helvetica-Bold", 14)
    c.drawString(LEFT, y, "PREVISÃO ORÇAMENTÁRIA 2025")
    c.setFont("Helvetica", 10)
    y -= 16
    c.drawString(LEFT, y, condo.name)
    y -= 15
    c.drawString(LEFT, y, f"Aprovada na assembleia geral ordinária de {approved_on}")
    y -= 30
    c.setFont("Helvetica-Bold", 10)
    c.drawString(LEFT, y, "Categoria")
    c.drawRightString(WIDTH - LEFT, y, "Valor mensal (R$)")
    c.setFont("Helvetica", 10)
    total = Decimal(0)
    for display, amount in condo.budget.values():
        y -= ROW + 2
        c.drawString(LEFT, y, display)
        c.drawRightString(WIDTH - LEFT, y, brl(amount))
        total += amount
    y -= ROW + 6
    c.setFont("Helvetica-Bold", 10)
    c.drawString(LEFT, y, "Total mensal")
    c.drawRightString(WIDTH - LEFT, y, brl(total))
    c.showPage()
    c.save()
    return buf.getvalue()


def penalty_notice(condo: CondoSpec, p: PenaltySpec) -> bytes:
    buf = io.BytesIO()
    c = _canvas(buf, f"Notificação {p.unit} {p.issued_on}")
    y = HEIGHT - 70
    c.setFont("Helvetica-Bold", 13)
    c.drawString(LEFT, y, "NOTIFICAÇÃO DE INFRAÇÃO AO REGIMENTO INTERNO")
    c.setFont("Helvetica", 10)
    y -= 16
    c.drawString(LEFT, y, condo.name)
    y -= 30
    c.setFont("Helvetica", 11)
    lines = [
        f"Unidade: {p.unit}",
        f"Condômino(a): {p.resident}",
        f"Data: {d(p.issued_on)}",
        f"Infração: {p.infraction}",
        f"Penalidade aplicada: {p.kind}",
        f"Valor: R$ {brl(p.amount)}" if p.amount is not None else "Valor: não se aplica",
        "Fundamento: item 8.1 do Regimento Interno.",
    ]
    for line in lines:
        y -= 22
        c.drawString(LEFT, y, line)
    y -= 40
    c.setFont("Helvetica", 10)
    c.drawString(LEFT, y, "O(a) condômino(a) poderá apresentar defesa por escrito no prazo de dez dias.")
    y -= 50
    c.drawString(LEFT, y, f"{condo.manager} — Síndico(a)")
    c.showPage()
    c.save()
    return buf.getvalue()
