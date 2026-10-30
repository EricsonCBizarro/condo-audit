"""Command line entry point: `condo-audit --help`."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Annotated

import typer
from redis import Redis

from condo_audit.db import Database
from condo_audit.log import configure_logging
from condo_audit.queue import ReliableQueue
from condo_audit.runs import RunRepository
from condo_audit.settings import get_settings
from condo_audit.storage import S3DocumentStore
from condo_audit.worker import Worker, default_worker_id

app = typer.Typer(no_args_is_help=True, add_completion=False, help="condo-audit pipeline")
storage_app = typer.Typer(no_args_is_help=True, help="Object storage helpers")
synth_app = typer.Typer(no_args_is_help=True, help="Synthetic data generator")
app.add_typer(storage_app, name="storage")
app.add_typer(synth_app, name="synth")


@app.callback()
def _setup() -> None:
    configure_logging(os.environ.get("LOG_LEVEL", "INFO"), os.environ.get("LOG_JSON", "1") == "1")


@app.command()
def worker() -> None:
    """Consume pipeline jobs until SIGTERM."""
    from condo_audit.handlers import build_handlers  # noqa: PLC0415 - heavy imports only for the worker

    settings = get_settings()
    db = Database.from_settings(settings)
    queue = ReliableQueue(Redis.from_url(settings.redis_url), settings.jobs_key, default_worker_id())
    store = S3DocumentStore.from_settings(settings)
    store.ensure_bucket()
    w = Worker(
        queue,
        RunRepository(db),
        build_handlers(db, store, settings),
        max_attempts=settings.max_attempts,
        retry_base_seconds=settings.retry_base_seconds,
    )
    w.install_signal_handlers()
    try:
        w.run_forever()
    finally:
        db.close()


@storage_app.command("ensure-bucket")
def ensure_bucket() -> None:
    """Create the documents bucket if it does not exist."""
    created = S3DocumentStore.from_settings(get_settings()).ensure_bucket()
    typer.echo("bucket created" if created else "bucket already exists")


@synth_app.command("generate")
def synth_generate(
    out: Annotated[Path, typer.Option(help="Output directory")] = Path("data/synthetic"),
    seed: Annotated[int, typer.Option(help="Random seed (same seed, same bytes)")] = 42,
) -> None:
    """Generate the fictional condominiums, their PDFs and the ground truth."""
    from condo_audit.synth.generator import generate  # noqa: PLC0415

    manifest = generate(out, seed)
    for condo in manifest["condominiums"]:
        scanned = sum(1 for d in condo["documents"] if d["scanned"])
        typer.echo(f"{condo['slug']}: {len(condo['documents'])} documents ({scanned} scanned)")
    typer.echo(f"Written to {out} (manifest.json, ground_truth.json)")


@app.command("eval")
def evaluate_command(
    ground_truth: Annotated[Path, typer.Option(help="ground_truth.json from the generator")] = Path(
        "data/synthetic/ground_truth.json"
    ),
    min_precision: Annotated[float, typer.Option(help="Fail below this overall precision")] = 0.9,
    min_recall: Annotated[float, typer.Option(help="Fail below this overall recall")] = 0.9,
) -> None:
    """Compare active findings with the planted irregularities."""
    from condo_audit.evaluation.loader import load_findings, load_ground_truth  # noqa: PLC0415
    from condo_audit.evaluation.metrics import evaluate  # noqa: PLC0415

    expected = load_ground_truth(ground_truth)
    slugs = sorted({e.condominium for e in expected} | _slugs(ground_truth))
    db = Database.from_settings(get_settings())
    try:
        report = evaluate(expected, load_findings(db, slugs))
    finally:
        db.close()

    typer.echo(f"{'rule':<30} {'tp':>3} {'fp':>3} {'fn':>3} {'precision':>9} {'recall':>7}")
    for code in sorted(report.by_rule):
        s = report.by_rule[code]
        typer.echo(
            f"{code:<30} {s.true_positives:>3} {s.false_positives:>3} {s.false_negatives:>3} "
            f"{s.precision:>9.0%} {s.recall:>7.0%}"
        )
    t = report.total
    typer.echo(
        f"{'TOTAL':<30} {t.true_positives:>3} {t.false_positives:>3} {t.false_negatives:>3} "
        f"{t.precision:>9.0%} {t.recall:>7.0%}"
    )
    for e in report.missed:
        typer.echo(f"  missed: {e.condominium} {e.rule_code} {e.period} ({e.note})")
    for f in report.unexpected:
        typer.echo(f"  unexpected: {f.condominium} {f.rule_code} {f.period} — {f.title}")
    if t.precision < min_precision or t.recall < min_recall:
        typer.echo(f"FAILED: precision/recall below {min_precision:.0%}/{min_recall:.0%}", err=True)
        raise typer.Exit(code=1)


def _slugs(ground_truth: Path) -> set[str]:
    import json  # noqa: PLC0415

    return {c["slug"] for c in json.loads(ground_truth.read_text())["condominiums"]}


@app.command()
def report(
    condominium: Annotated[str, typer.Option(help="Condominium slug")],
    out: Annotated[Path | None, typer.Option(help="Write to this file instead of stdout")] = None,
) -> None:
    """Markdown audit report for one condominium."""
    from condo_audit.report.markdown import render  # noqa: PLC0415

    db = Database.from_settings(get_settings())
    try:
        text = render(db, condominium)
    finally:
        db.close()
    if out:
        out.write_text(text)
        typer.echo(f"Report written to {out}")
    else:
        typer.echo(text)


if __name__ == "__main__":
    app()
