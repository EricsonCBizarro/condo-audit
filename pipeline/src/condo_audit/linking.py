"""Match statement debits to the receipts attached to the same statement.

Score of a (debit, receipt) pair:
    amount equal (cents)          +0.6
    payee words in description    +0.3
    paid within 3 days            +0.1

Pairs are assigned greedily, best score first, one receipt per debit. A pair
scoring 0.4 without equal amounts is kept on purpose: same payee and date but
a different amount is exactly what RECEIPT_AMOUNT_MISMATCH looks for.

Links are suggestions. Confirmed or rejected links (human decisions) are never
touched; only automatic suggestions are recomputed.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from condo_audit.db import Connection
from condo_audit.extraction.text import significant_tokens

MIN_SCORE = Decimal("0.4")


@dataclass(frozen=True, slots=True)
class Debit:
    id: int
    description: str
    amount: Decimal
    entry_date: date | None


@dataclass(frozen=True, slots=True)
class ReceiptRef:
    id: int
    payee: str | None
    amount: Decimal | None
    paid_on: date | None


def score(debit: Debit, receipt: ReceiptRef) -> Decimal:
    value = Decimal(0)
    if receipt.amount is not None and abs(debit.amount) == abs(receipt.amount):
        value += Decimal("0.6")
    if receipt.payee and significant_tokens(debit.description) & significant_tokens(receipt.payee):
        value += Decimal("0.3")
    if debit.entry_date and receipt.paid_on and abs((debit.entry_date - receipt.paid_on).days) <= 3:
        value += Decimal("0.1")
    return value


def assign(
    debits: list[Debit], receipts: list[ReceiptRef], blocked: set[tuple[int, int]] | None = None
) -> list[tuple[int, int, Decimal]]:
    """Greedy one-to-one assignment: [(debit_id, receipt_id, score)]."""
    blocked = blocked or set()
    pairs = sorted(
        ((score(d, r), d.id, r.id) for d in debits for r in receipts if (d.id, r.id) not in blocked),
        key=lambda t: (-t[0], t[1], t[2]),
    )
    used_debits: set[int] = set()
    used_receipts: set[int] = set()
    result = []
    for value, debit_id, receipt_id in pairs:
        if value < MIN_SCORE or debit_id in used_debits or receipt_id in used_receipts:
            continue
        used_debits.add(debit_id)
        used_receipts.add(receipt_id)
        result.append((debit_id, receipt_id, value))
    return result


def link_document(conn: Connection, document_id: int) -> int:
    debits = [
        Debit(int(str(r["id"])), str(r["description"]), Decimal(str(r["amount"])), r["entry_date"])
        for r in conn.execute(
            """
            select id, description, amount, entry_date from statement_entries
            where document_id = %s and kind = 'transaction' and amount < 0
            """,
            (document_id,),
        ).fetchall()
    ]
    receipts = [
        ReceiptRef(
            int(str(r["id"])),
            r["payee"] if r["payee"] is None else str(r["payee"]),
            None if r["amount"] is None else Decimal(str(r["amount"])),
            r["paid_on"],
        )
        for r in conn.execute(
            "select id, payee, amount, paid_on from receipts where document_id = %s", (document_id,)
        ).fetchall()
    ]
    decided = conn.execute(
        """
        select l.statement_entry_id, l.receipt_id, l.status from entry_receipt_links l
        join statement_entries e on e.id = l.statement_entry_id
        where e.document_id = %s and l.status <> 'suggested'
        """,
        (document_id,),
    ).fetchall()
    rejected = {
        (int(str(r["statement_entry_id"])), int(str(r["receipt_id"]))) for r in decided if r["status"] == "rejected"
    }
    confirmed_debits = {int(str(r["statement_entry_id"])) for r in decided if r["status"] == "confirmed"}
    confirmed_receipts = {int(str(r["receipt_id"])) for r in decided if r["status"] == "confirmed"}

    conn.execute(
        """
        delete from entry_receipt_links l using statement_entries e
        where e.id = l.statement_entry_id and e.document_id = %s and l.status = 'suggested' and l.origin = 'auto'
        """,
        (document_id,),
    )
    pairs = assign(
        [d for d in debits if d.id not in confirmed_debits],
        [r for r in receipts if r.id not in confirmed_receipts],
        blocked=rejected,
    )
    with conn.cursor() as cur:
        cur.executemany(
            """
            insert into entry_receipt_links (statement_entry_id, receipt_id, score, status, origin, created_at, updated_at)
            values (%s, %s, %s, 'suggested', 'auto', now(), now())
            on conflict (statement_entry_id, receipt_id) do nothing
            """,
            pairs,
        )
    return len(pairs)
