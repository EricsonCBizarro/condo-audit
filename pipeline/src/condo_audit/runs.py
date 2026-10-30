"""pipeline_runs bookkeeping. The API inserts the row (status `queued`);
from then on the worker owns the status."""

from __future__ import annotations

import json
from typing import Any, Protocol
from uuid import UUID

from condo_audit.db import Database


class RunTracker(Protocol):
    def mark_running(self, job_id: UUID, attempt: int) -> None: ...
    def mark_succeeded(self, job_id: UUID, stats: dict[str, Any]) -> None: ...
    def mark_retrying(self, job_id: UUID, error: str) -> None: ...
    def mark_dead(self, job_id: UUID, error: str) -> None: ...


class RunRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def mark_running(self, job_id: UUID, attempt: int) -> None:
        self._update(
            job_id,
            "status = 'running', attempts = %(attempts)s, started_at = now(), error = null",
            {"attempts": attempt + 1},
        )

    def mark_succeeded(self, job_id: UUID, stats: dict[str, Any]) -> None:
        self._update(
            job_id,
            "status = 'succeeded', finished_at = now(), stats = %(stats)s::jsonb",
            {"stats": json.dumps(stats, default=str)},
        )

    def mark_retrying(self, job_id: UUID, error: str) -> None:
        self._update(job_id, "status = 'queued', error = %(error)s", {"error": error[:4000]})

    def mark_dead(self, job_id: UUID, error: str) -> None:
        self._update(job_id, "status = 'dead', finished_at = now(), error = %(error)s", {"error": error[:4000]})

    def _update(self, job_id: UUID, assignments: str, params: dict[str, Any]) -> None:
        with self._db.transaction() as conn:
            conn.execute(
                f"update pipeline_runs set {assignments}, updated_at = now() where id = %(id)s",  # noqa: S608
                {**params, "id": str(job_id)},
            )
