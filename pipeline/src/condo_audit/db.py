"""PostgreSQL access. The schema is owned by the API's migrations; this
package only reads and writes rows (see docs/adr/0002)."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import psycopg
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from condo_audit.settings import Settings

Connection = psycopg.Connection[dict[str, Any]]


class Database:
    def __init__(self, dsn: str, min_size: int = 1, max_size: int = 4) -> None:
        self._pool: ConnectionPool[Connection] = ConnectionPool(
            dsn,
            min_size=min_size,
            max_size=max_size,
            kwargs={"row_factory": dict_row},
            open=True,
        )

    @classmethod
    def from_settings(cls, settings: Settings) -> Database:
        return cls(settings.database_url.get_secret_value())

    @contextmanager
    def transaction(self) -> Iterator[Connection]:
        """One connection, one transaction: commit on success, rollback on error."""
        with self._pool.connection() as conn, conn.transaction():
            yield conn

    def close(self) -> None:
        self._pool.close()
