# ADR-0002 — A small JSON job contract on a reliable Redis queue

**Status:** accepted

## Context

The API must hand work to the Python worker. Laravel's queue payload format is
PHP-specific (serialized jobs) and not meant to be consumed by other runtimes.

## Decision

- The API publishes a plain JSON message to a Redis list. Its shape is
  [`contracts/job.schema.json`](../../contracts/job.schema.json) (JSON
  Schema 2020-12), with a `schema_version` field.
- **Both sides test against the same schema file**: PHPUnit validates what the
  API publishes (opis/json-schema); pytest validates what the Python model
  serializes and accepts a message captured from the API.
- The worker uses the reliable-queue pattern: `BLMOVE` into a per-worker
  processing list, `LREM` on success, a delayed sorted set with exponential
  backoff for retries, a dead-letter list after `PIPELINE_MAX_ATTEMPTS`, and
  heartbeat keys so a crashed worker's in-flight jobs are moved back.
- `pipeline_runs` is the observable state of every job. The API inserts the
  row **before** publishing; the worker owns every later transition.
- A correlation id travels HTTP header → log context → message → worker logs.

## Consequences

- Any runtime can produce or consume jobs; the contract is explicit and
  versioned.
- At-least-once delivery: handlers are idempotent (upserts by natural key and
  fingerprints, see ADR-0006).
- We maintain ~100 lines of queue code instead of using a framework queue.
  Acceptable for two job types; revisit (e.g. Redis Streams consumer groups or
  a managed queue) if throughput or job variety grows.
