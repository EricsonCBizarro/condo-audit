from __future__ import annotations

from typing import Any
from uuid import UUID

from redis import Redis

from condo_audit.jobs import JobMessage, JobType
from condo_audit.queue import ReliableQueue
from condo_audit.worker import Worker
from tests.conftest import make_message


class FakeRuns:
    def __init__(self) -> None:
        self.events: list[tuple[str, UUID]] = []

    def mark_running(self, job_id: UUID, attempt: int) -> None:
        self.events.append(("running", job_id))

    def mark_succeeded(self, job_id: UUID, stats: dict[str, Any]) -> None:
        self.events.append(("succeeded", job_id))

    def mark_retrying(self, job_id: UUID, error: str) -> None:
        self.events.append(("retrying", job_id))

    def mark_dead(self, job_id: UUID, error: str) -> None:
        self.events.append(("dead", job_id))


def _worker(redis_client: Redis, handler: Any, max_attempts: int = 2) -> tuple[Worker, ReliableQueue, FakeRuns]:
    queue = ReliableQueue(redis_client, "t:jobs", "w1")
    runs = FakeRuns()
    worker = Worker(
        queue,
        runs,
        {JobType.DOCUMENT_PROCESS: handler},
        max_attempts=max_attempts,
        retry_base_seconds=0,
    )
    return worker, queue, runs


def test_a_successful_job_is_acknowledged(redis_client: Redis) -> None:
    worker, queue, runs = _worker(redis_client, lambda m: {"pages": 3})
    message = make_message()
    queue.push(message)

    assert worker.run_once() is True
    assert [e for e, _ in runs.events] == ["running", "succeeded"]
    assert queue.depth() == {"queued": 0, "delayed": 0, "dead": 0}


def test_a_failing_job_is_retried_then_buried(redis_client: Redis) -> None:
    def boom(message: JobMessage) -> dict[str, Any]:
        raise RuntimeError("OCR engine crashed")

    worker, queue, runs = _worker(redis_client, boom, max_attempts=2)
    queue.push(make_message())

    worker.run_once()  # attempt 0 → retry
    worker.run_once()  # attempt 1 → dead

    assert [e for e, _ in runs.events] == ["running", "retrying", "running", "dead"]
    assert queue.depth()["dead"] == 1


def test_jobs_without_a_handler_go_to_the_dead_letter_list(redis_client: Redis) -> None:
    worker, queue, runs = _worker(redis_client, lambda m: {})
    queue.push(make_message(JobType.AUDIT_RUN))

    worker.run_once()

    assert runs.events[-1][0] == "dead"
    assert queue.depth()["dead"] == 1
