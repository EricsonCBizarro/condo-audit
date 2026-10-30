# pipeline — `condo_audit`

Python 3.12 package with the document pipeline and the audit rules engine.
Run everything through the root `Makefile`; to work on it directly:

```bash
uv sync                       # creates .venv with dev dependencies
uv run pytest -m "not integration"
uv run ruff check src tests && uv run mypy
uv run condo-audit --help     # worker · synth · eval · report · storage
```

| Module | Responsibility |
|---|---|
| `worker.py`, `queue.py`, `jobs.py`, `runs.py` | reliable Redis queue consumer and job bookkeeping |
| `documents/` | native text or Tesseract OCR → positioned words → lines |
| `extraction/` | page types, money/dates, statement reconciliation, receipts, governance documents |
| `linking.py` | debit ↔ receipt matching |
| `processing.py` | `document.process` handler (one transaction per document) |
| `audit/` | typed context, ten rules, runner (`audit.run` handler) |
| `synth/` | the fictional world, PDF rendering, scan simulation, ground truth |
| `evaluation/`, `report/` | precision/recall against ground truth, Markdown report |

Integration tests (`-m integration`) need `DATABASE_URL` pointing at a
migrated `condo_audit_test` database; `make test-pipeline` takes care of it.
