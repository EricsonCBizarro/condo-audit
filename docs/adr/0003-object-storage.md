# ADR-0003 — S3-compatible object storage, SeaweedFS for local development

**Status:** accepted

## Context

Original documents are the bronze layer: immutable, addressed by SHA-256, and
the evidence every finding points back to. They do not belong in the database
or on a container filesystem.

## Decision

- Store originals in any S3-compatible bucket, keyed by
  `condominiums/<id>/documents/<sha256>.pdf`. The API writes through Laravel's
  Flysystem S3 driver; the worker reads with boto3.
- Local development uses **SeaweedFS** with its S3 gateway. MinIO was the
  first choice, but its community container images stopped being published
  on public registries, which would break `make up` for a fresh clone.

## Consequences

- Moving to AWS S3 (or GCS/R2 in S3 mode) is configuration only: endpoint,
  credentials and bucket.
- Deduplication is per condominium (`unique(condominium_id, sha256)`):
  re-uploading the same bytes returns the existing document.
