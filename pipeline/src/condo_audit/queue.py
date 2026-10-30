"""Reliable queue on Redis lists.

    jobs ──BLMOVE──▶ processing:<worker> ──ack──▶ (removed)
                         │
                         ├─ failure, attempts left ─▶ delayed (zset, backoff) ─▶ jobs
                         └─ failure, no attempts   ─▶ dead (with error)

A crashed worker leaves its messages in its own processing list; any worker
whose heartbeat key is gone gets its list moved back to `jobs` by
`recover_orphans`, so no job is lost and none is processed twice while its
owner is alive.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import UTC, datetime

from pydantic import ValidationError
from redis import Redis

from condo_audit.jobs import JobMessage

# Moves every due message from the delayed set back to the main list
# atomically, so two workers never promote the same message.
_PROMOTE_DUE = """
local due = redis.call('ZRANGEBYSCORE', KEYS[1], '-inf', ARGV[1], 'LIMIT', 0, 100)
for _, raw in ipairs(due) do
  redis.call('ZREM', KEYS[1], raw)
  redis.call('RPUSH', KEYS[2], raw)
end
return #due
"""


@dataclass(frozen=True, slots=True)
class Reservation:
    raw: str
    message: JobMessage | None
    error: str | None = None


class ReliableQueue:
    def __init__(self, redis: Redis, jobs_key: str, worker_id: str, heartbeat_ttl: int = 30) -> None:
        self._redis = redis
        self.jobs_key = jobs_key
        self.delayed_key = f"{jobs_key}:delayed"
        self.dead_key = f"{jobs_key}:dead"
        self.worker_id = worker_id
        self.processing_key = f"{jobs_key}:processing:{worker_id}"
        self._heartbeat_key = f"{jobs_key}:worker:{worker_id}"
        self._heartbeat_ttl = heartbeat_ttl
        self._promote = redis.register_script(_PROMOTE_DUE)

    def push(self, message: JobMessage) -> None:
        self._redis.rpush(self.jobs_key, message.to_json())

    def reserve(self, timeout: float = 5.0) -> Reservation | None:
        self._promote(keys=[self.delayed_key, self.jobs_key], args=[time.time()])
        if timeout < 1:  # non-blocking poll (BLMOVE with 0 would block forever)
            raw = self._redis.lmove(self.jobs_key, self.processing_key, "LEFT", "RIGHT")
        else:
            raw = self._redis.blmove(self.jobs_key, self.processing_key, int(timeout), "LEFT", "RIGHT")
        if raw is None:
            return None
        text = raw.decode() if isinstance(raw, bytes) else str(raw)
        try:
            return Reservation(text, JobMessage.model_validate_json(text))
        except ValidationError as exc:
            return Reservation(text, None, error=str(exc))

    def ack(self, reservation: Reservation) -> None:
        self._redis.lrem(self.processing_key, 1, reservation.raw)

    def retry(self, reservation: Reservation, message: JobMessage, delay_seconds: float) -> None:
        pipe = self._redis.pipeline(transaction=True)
        pipe.lrem(self.processing_key, 1, reservation.raw)
        pipe.zadd(self.delayed_key, {message.next_attempt().to_json(): time.time() + delay_seconds})
        pipe.execute()

    def bury(self, reservation: Reservation, error: str) -> None:
        record = json.dumps({"raw": reservation.raw, "error": error[:2000], "buried_at": datetime.now(UTC).isoformat()})
        pipe = self._redis.pipeline(transaction=True)
        pipe.lrem(self.processing_key, 1, reservation.raw)
        pipe.rpush(self.dead_key, record)
        pipe.execute()

    def heartbeat(self) -> None:
        self._redis.set(self._heartbeat_key, "1", ex=self._heartbeat_ttl)

    def stop(self) -> None:
        self._redis.delete(self._heartbeat_key)

    def recover_orphans(self) -> int:
        """Requeue messages held by workers whose heartbeat expired."""
        recovered = 0
        for key in self._redis.scan_iter(match=f"{self.jobs_key}:processing:*"):
            name = key.decode() if isinstance(key, bytes) else str(key)
            owner = name.rsplit(":", 1)[-1]
            if owner == self.worker_id or self._redis.exists(f"{self.jobs_key}:worker:{owner}"):
                continue
            while self._redis.lmove(name, self.jobs_key, "LEFT", "RIGHT") is not None:
                recovered += 1
        return recovered

    def depth(self) -> dict[str, int]:
        return {
            "queued": int(self._redis.llen(self.jobs_key)),
            "delayed": int(self._redis.zcard(self.delayed_key)),
            "dead": int(self._redis.llen(self.dead_key)),
        }
