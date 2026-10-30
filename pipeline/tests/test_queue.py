from __future__ import annotations

import time

from redis import Redis

from condo_audit.queue import ReliableQueue
from tests.conftest import make_message


def test_reserve_moves_the_message_to_the_processing_list(redis_client: Redis) -> None:
    queue = ReliableQueue(redis_client, "t:jobs", "w1")
    message = make_message()
    queue.push(message)

    reservation = queue.reserve(timeout=0)

    assert reservation is not None
    assert reservation.message == message
    assert redis_client.llen("t:jobs") == 0
    assert redis_client.llen("t:jobs:processing:w1") == 1

    queue.ack(reservation)
    assert redis_client.llen("t:jobs:processing:w1") == 0


def test_retry_schedules_the_next_attempt_with_a_delay(redis_client: Redis) -> None:
    queue = ReliableQueue(redis_client, "t:jobs", "w1")
    queue.push(make_message())
    reservation = queue.reserve(timeout=0)
    assert reservation is not None
    assert reservation.message is not None

    queue.retry(reservation, reservation.message, delay_seconds=0.2)

    assert queue.reserve(timeout=0) is None  # not due yet
    time.sleep(0.25)
    retried = queue.reserve(timeout=0)
    assert retried is not None
    assert retried.message is not None
    assert retried.message.attempt == 1
    assert retried.message.job_id == reservation.message.job_id


def test_malformed_messages_are_buried_with_the_error(redis_client: Redis) -> None:
    queue = ReliableQueue(redis_client, "t:jobs", "w1")
    redis_client.rpush("t:jobs", '{"not": "a job"}')

    reservation = queue.reserve(timeout=0)
    assert reservation is not None
    assert reservation.message is None
    queue.bury(reservation, reservation.error or "")

    assert queue.depth() == {"queued": 0, "delayed": 0, "dead": 1}
    assert redis_client.llen("t:jobs:processing:w1") == 0


def test_orphaned_messages_of_a_dead_worker_are_recovered(redis_client: Redis) -> None:
    crashed = ReliableQueue(redis_client, "t:jobs", "crashed", heartbeat_ttl=1)
    crashed.heartbeat()
    crashed.push(make_message())
    assert crashed.reserve(timeout=0) is not None  # taken, never acked

    survivor = ReliableQueue(redis_client, "t:jobs", "survivor")
    assert survivor.recover_orphans() == 0  # owner still alive

    redis_client.delete("t:jobs:worker:crashed")  # heartbeat expired
    assert survivor.recover_orphans() == 1
    assert survivor.reserve(timeout=0) is not None
