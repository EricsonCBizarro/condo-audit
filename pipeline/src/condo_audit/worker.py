"""Worker loop: reserve → run handler → ack / retry with backoff / bury."""

from __future__ import annotations

import signal
import socket
import time
import traceback
from collections.abc import Callable, Mapping
from types import FrameType
from typing import Any
from uuid import uuid4

import structlog

from condo_audit.jobs import JobMessage, JobType
from condo_audit.log import get_logger
from condo_audit.queue import ReliableQueue, Reservation
from condo_audit.runs import RunTracker

JobHandler = Callable[[JobMessage], dict[str, Any]]

log = get_logger(__name__)


def default_worker_id() -> str:
    return f"{socket.gethostname()}-{uuid4().hex[:8]}"


class Worker:
    def __init__(
        self,
        queue: ReliableQueue,
        runs: RunTracker,
        handlers: Mapping[JobType, JobHandler],
        max_attempts: int = 3,
        retry_base_seconds: float = 5.0,
    ) -> None:
        self._queue = queue
        self._runs = runs
        self._handlers = handlers
        self._max_attempts = max_attempts
        self._retry_base = retry_base_seconds
        self._stopping = False

    def stop(self, *_: object) -> None:
        self._stopping = True

    def install_signal_handlers(self) -> None:
        def _handler(signum: int, frame: FrameType | None) -> None:
            log.info("worker.stopping", signal=signum)
            self.stop()

        signal.signal(signal.SIGTERM, _handler)
        signal.signal(signal.SIGINT, _handler)

    def run_forever(self, poll_timeout: float = 5.0) -> None:
        self._queue.heartbeat()
        recovered = self._queue.recover_orphans()
        log.info("worker.started", worker_id=self._queue.worker_id, recovered_orphans=recovered)
        try:
            while not self._stopping:
                self._queue.heartbeat()
                self.run_once(poll_timeout)
        finally:
            self._queue.stop()
            log.info("worker.stopped")

    def run_once(self, poll_timeout: float = 0.1) -> bool:
        """Process at most one job. Returns True when a job was handled."""
        reservation = self._queue.reserve(poll_timeout)
        if reservation is None:
            return False
        if reservation.message is None:
            log.error("job.malformed", error=reservation.error)
            self._queue.bury(reservation, f"malformed message: {reservation.error}")
            return True
        self._handle(reservation, reservation.message)
        return True

    def _handle(self, reservation: Reservation, message: JobMessage) -> None:
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            correlation_id=message.correlation_id,
            job_id=str(message.job_id),
            job_type=message.type.value,
            condominium_id=message.condominium_id,
            attempt=message.attempt,
        )
        handler = self._handlers.get(message.type)
        if handler is None:
            self._runs.mark_dead(message.job_id, f"no handler for {message.type}")
            self._queue.bury(reservation, f"no handler for {message.type}")
            return

        self._runs.mark_running(message.job_id, message.attempt)
        started = time.perf_counter()
        try:
            stats = handler(message)
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}\n{traceback.format_exc(limit=5)}"
            if message.attempt + 1 >= self._max_attempts:
                log.error("job.dead", error=str(exc))
                self._runs.mark_dead(message.job_id, error)
                self._queue.bury(reservation, error)
            else:
                delay = self._retry_base * (2**message.attempt)
                log.warning("job.retry", error=str(exc), retry_in_seconds=delay)
                self._runs.mark_retrying(message.job_id, error)
                self._queue.retry(reservation, message, delay)
            return

        stats["duration_ms"] = round((time.perf_counter() - started) * 1000)
        self._runs.mark_succeeded(message.job_id, stats)
        self._queue.ack(reservation)
        log.info("job.succeeded", **{k: v for k, v in stats.items() if isinstance(v, int | float | str)})
