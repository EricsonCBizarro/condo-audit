"""Writes the synthetic world to disk:

<out>/manifest.json           condominiums + documents to ingest
<out>/ground_truth.json       every planted irregularity
<out>/<slug>/**/*.pdf         the documents
"""

from __future__ import annotations

import hashlib
import json
import random
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

from condo_audit import __version__
from condo_audit.formatting import d
from condo_audit.synth import render, texts
from condo_audit.synth.scan import scanned
from condo_audit.synth.scenario import CondoSpec, build_world


@dataclass(frozen=True)
class GeneratedDocument:
    path: str
    type: str
    title: str
    reference_period: str | None
    scanned: bool


def _write(out: Path, rel: str, data: bytes) -> None:
    target = out / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)


def _documents(condo: CondoSpec, rng: random.Random) -> list[tuple[GeneratedDocument, bytes]]:
    s = condo.slug
    docs: list[tuple[GeneratedDocument, bytes]] = []

    def add(rel: str, type_: str, title: str, period: str | None, pdf: bytes, key: str | None = None) -> None:
        is_scanned = (key or type_) in condo.scanned
        data = scanned(pdf, rng) if is_scanned else pdf
        docs.append((GeneratedDocument(f"{s}/{rel}", type_, title, period, is_scanned), data))

    add(
        "governance/convencao.pdf",
        "convention",
        "Convenção do condomínio",
        None,
        render.text_document("Convenção", texts.convention(condo)),
    )
    add(
        "governance/regimento-interno.pdf",
        "bylaws",
        "Regimento interno",
        None,
        render.text_document("Regimento interno", texts.bylaws(condo)),
    )
    ago = next(m for m in condo.meetings if m.kind == "ORDINÁRIA")
    add(
        "governance/previsao-orcamentaria-2025.pdf",
        "budget",
        "Previsão orçamentária 2025",
        "2025-01",
        render.budget(condo, d(ago.held_on)),
    )
    for meeting in condo.meetings:
        tag = "ago" if meeting.kind == "ORDINÁRIA" else "age"
        stamp = meeting.held_on.isoformat()
        period = f"{meeting.held_on:%Y-%m}"
        add(
            f"meetings/{stamp}-edital-{tag}.pdf",
            "meeting_notice",
            f"Edital de convocação {tag.upper()} {meeting.held_on:%d/%m/%Y}",
            period,
            render.text_document("Edital", texts.meeting_notice(condo, meeting)),
        )
        add(
            f"meetings/{stamp}-ata-{tag}.pdf",
            "meeting_minutes",
            f"Ata {tag.upper()} {meeting.held_on:%d/%m/%Y}",
            period,
            render.text_document("Ata", texts.meeting_minutes(condo, meeting)),
        )
    for st in condo.statements:
        period = f"{st.period:%Y-%m}"
        add(
            f"statements/{period}-balancete.pdf",
            "financial_statement",
            f"Balancete {st.period:%m/%Y}",
            period,
            render.financial_statement(condo, st),
            key=f"financial_statement:{period}",
        )
    for p in condo.penalties:
        add(
            f"penalties/{p.issued_on.isoformat()}-notificacao-{p.unit}.pdf",
            "penalty_notice",
            f"Notificação {p.unit} {p.issued_on:%d/%m/%Y}",
            f"{p.issued_on:%Y-%m}",
            render.penalty_notice(condo, p),
        )
    return docs


def _money(value: Decimal | None) -> str | None:
    return None if value is None else f"{value:.2f}"


def generate(out: Path, seed: int = 42) -> dict[str, Any]:
    """Generate everything under `out`; returns the manifest."""
    out.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed ^ 0x5CA9)
    world = build_world(seed)
    manifest: dict[str, Any] = {"seed": seed, "generator": f"condo-audit {__version__}", "condominiums": []}
    truth: dict[str, Any] = {"seed": seed, "condominiums": []}

    for condo in world:
        entries = []
        for doc, data in _documents(condo, rng):
            _write(out, doc.path, data)
            entries.append(
                {
                    "path": doc.path,
                    "type": doc.type,
                    "title": doc.title,
                    "reference_period": doc.reference_period,
                    "scanned": doc.scanned,
                    "sha256": hashlib.sha256(data).hexdigest(),
                }
            )
        manifest["condominiums"].append(
            {
                "slug": condo.slug,
                "name": condo.name,
                "tax_id": condo.tax_id,
                "city": condo.city,
                "settings": {"monthly_fee": f"{condo.monthly_fee:.2f}"},
                "documents": entries,
            }
        )
        truth["condominiums"].append(
            {
                "slug": condo.slug,
                "expected_findings": [
                    {"rule_code": g.rule_code, "period": g.period, "amount": _money(g.amount), "note": g.note}
                    for g in condo.expected
                ],
            }
        )

    (out / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    (out / "ground_truth.json").write_text(json.dumps(truth, indent=2, ensure_ascii=False) + "\n")
    return manifest
