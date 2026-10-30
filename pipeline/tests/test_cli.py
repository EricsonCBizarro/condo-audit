from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path

import pytest
import structlog
from typer.testing import CliRunner

from condo_audit.cli import app

runner = CliRunner()


@pytest.fixture(autouse=True)
def _restore_logging() -> Iterator[None]:
    # The CLI configures structlog to print to the runner's (temporary) stdout.
    yield
    structlog.reset_defaults()


def test_help_lists_the_commands() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for command in ("worker", "synth", "eval", "report", "storage"):
        assert command in result.output


def test_synth_generate_writes_manifest_and_ground_truth(tmp_path: Path) -> None:
    result = runner.invoke(app, ["synth", "generate", "--out", str(tmp_path), "--seed", "7"])

    assert result.exit_code == 0, result.output
    manifest = json.loads((tmp_path / "manifest.json").read_text())
    assert [c["slug"] for c in manifest["condominiums"]] == [
        "residencial-jardim-das-acacias",
        "edificio-mirante-do-vale",
    ]
    assert (tmp_path / "ground_truth.json").exists()
