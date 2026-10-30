# ADR-0008 — Shared schema multi-tenancy, enforced at the edges

**Status:** accepted

## Decision

- One database, every tenant-owned row carries `condominium_id`.
- Users belong to condominiums with a role (`owner`, `auditor`, `viewer`).
- Every route is nested under `/condominiums/{condominium}` with **scoped
  route bindings**: a document or finding id that exists but belongs to
  another condominium is a 404, never a leak. A policy on the condominium
  decides view/upload/review/audit.
- The worker re-checks tenancy too: a job can only touch a document of the
  condominium named in the message.
- Cross-tenant access is covered by dedicated tests (API and dashboard).

## Alternatives considered

- **Database per tenant:** strongest isolation, heavy operations for many
  small condominiums.
- **PostgreSQL row-level security:** a good second line of defence; planned
  once the API sets a per-request tenant setting, so that a bug in a query
  cannot cross tenants either.
