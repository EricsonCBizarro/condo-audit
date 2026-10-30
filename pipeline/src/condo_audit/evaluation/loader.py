from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

from condo_audit.db import Database
from condo_audit.evaluation.metrics import Detected, Expected


def load_ground_truth(path: Path) -> list[Expected]:
    data = json.loads(path.read_text())
    return [
        Expected(
            c["slug"],
            item["rule_code"],
            item["period"],
            Decimal(item["amount"]) if item["amount"] is not None else None,
            item.get("note", ""),
        )
        for c in data["condominiums"]
        for item in c["expected_findings"]
    ]


def load_findings(db: Database, slugs: list[str]) -> list[Detected]:
    with db.transaction() as conn:
        rows = conn.execute(
            """
            select c.slug, f.rule_code, f.period, f.amount, f.title from findings f
            join condominiums c on c.id = f.condominium_id
            where c.slug = any(%s) and f.is_active and f.category = 'irregularity'
            order by c.slug, f.rule_code, f.period
            """,
            (slugs,),
        ).fetchall()
    return [Detected(r["slug"], r["rule_code"], r["period"], r["amount"], r["title"]) for r in rows]
