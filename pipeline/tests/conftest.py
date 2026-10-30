from __future__ import annotations

import os
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from redis import Redis

from condo_audit.jobs import JobMessage, JobType

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def contracts_dir() -> Path:
    return Path(os.environ.get("CONTRACTS_PATH", REPO_ROOT / "contracts"))


def make_message(type_: JobType = JobType.DOCUMENT_PROCESS, **overrides: Any) -> JobMessage:
    data: dict[str, Any] = {
        "schema_version": 1,
        "job_id": uuid.uuid4(),
        "type": type_,
        "condominium_id": 1,
        "correlation_id": "test-correlation",
        "enqueued_at": datetime.now(UTC),
        "attempt": 0,
        "payload": {"document_id": 7} if type_ is JobType.DOCUMENT_PROCESS else {},
    }
    data.update(overrides)
    return JobMessage.model_validate(data)


@pytest.fixture
def redis_client() -> Iterator[Redis]:
    url = os.environ.get("REDIS_URL", "redis://localhost:56379/0")
    client = Redis.from_url(url.rsplit("/", 1)[0] + "/15")  # isolated test db
    try:
        client.ping()
    except Exception as exc:  # pragma: no cover - environment guard
        pytest.skip(f"Redis not reachable at {url}: {exc}")
    client.flushdb()
    yield client
    client.flushdb()
