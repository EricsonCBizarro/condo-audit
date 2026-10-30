from __future__ import annotations

import json
import re
from pathlib import Path

import pymupdf
import pytest

from condo_audit.synth.generator import generate
from condo_audit.synth.scenario import build_world
from condo_audit.synth.taxid import is_valid_cnpj

CNPJ_RE = re.compile(r"\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}")


@pytest.fixture(scope="module")
def generated(tmp_path_factory: pytest.TempPathFactory) -> Path:
    out = tmp_path_factory.mktemp("synthetic")
    generate(out, seed=42)
    return out


def _manifest(out: Path) -> dict:  # type: ignore[type-arg]
    return json.loads((out / "manifest.json").read_text())  # type: ignore[no-any-return]


def test_same_seed_produces_identical_files(generated: Path, tmp_path: Path) -> None:
    generate(tmp_path, seed=42)
    first = {d["path"]: d["sha256"] for c in _manifest(generated)["condominiums"] for d in c["documents"]}
    second = {d["path"]: d["sha256"] for c in _manifest(tmp_path)["condominiums"] for d in c["documents"]}
    assert first == second


def test_every_planted_irregularity_is_in_the_ground_truth(generated: Path) -> None:
    truth = json.loads((generated / "ground_truth.json").read_text())
    by_slug = {c["slug"]: c["expected_findings"] for c in truth["condominiums"]}

    assert len(by_slug["residencial-jardim-das-acacias"]) == 10
    assert len({f["rule_code"] for f in by_slug["residencial-jardim-das-acacias"]}) == 10
    assert by_slug["edificio-mirante-do-vale"] == []  # clean control group


def test_scanned_documents_have_no_text_layer(generated: Path) -> None:
    for condo in _manifest(generated)["condominiums"]:
        for doc in condo["documents"]:
            text = "".join(page.get_text() for page in pymupdf.open(generated / doc["path"]))
            assert bool(text.strip()) is not doc["scanned"], doc["path"]


def test_no_generated_tax_id_is_a_valid_cnpj(generated: Path) -> None:
    found: set[str] = set()
    for condo in _manifest(generated)["condominiums"]:
        found.add(condo["tax_id"])
        for doc in condo["documents"]:
            for page in pymupdf.open(generated / doc["path"]):
                found.update(CNPJ_RE.findall(page.get_text()))
    assert len(found) >= 3  # both condominiums + the foreign payer
    assert not [t for t in found if is_valid_cnpj(t)]


def test_unplanted_months_have_a_consistent_balance_chain() -> None:
    irregular, control = build_world(42)
    for condo, broken in ((irregular, {"2025-03"}), (control, set())):
        for st in condo.statements:
            running = st.opening
            breaks = 0
            for tx, printed in zip(st.transactions, st.printed_balances, strict=True):
                running += tx.amount
                if running != printed:
                    breaks += 1
                    running = printed
            assert (breaks == 1) is (f"{st.period:%Y-%m}" in broken), st.period


def test_months_are_chained_except_the_planted_gap() -> None:
    irregular, control = build_world(42)
    for condo, gaps in ((irregular, {"2025-09"}), (control, set())):
        for prev, cur in zip(condo.statements, condo.statements[1:], strict=False):
            assert (prev.closing != cur.opening) is (f"{cur.period:%Y-%m}" in gaps)
