# HTTP API (v1)

All endpoints except `health` and `auth/token` require a Sanctum bearer token.
Tenant-scoped resources live under `/api/v1/condominiums/{slug}`; ids from
another condominium return 404. Send `X-Correlation-Id` to trace a request
through the worker logs (one is generated otherwise and echoed back).

| Method | Path | Notes |
|---|---|---|
| GET | `/health` | PostgreSQL, Redis and storage checks (200 / 503) |
| POST | `/auth/token` | `email`, `password`, `device_name` → token |
| GET | `/condominiums` | condominiums of the current user |
| GET | `/condominiums/{slug}` | |
| GET | `/condominiums/{slug}/summary` | documents, findings by severity/rule, amount involved |
| GET | `/condominiums/{slug}/documents` | `type`, `status`, `per_page` |
| POST | `/condominiums/{slug}/documents` | multipart: `file` (PDF), `type`, `title?`, `reference_period?` (YYYY-MM) → **202** + pipeline run; same bytes again → 200 `duplicate: true` |
| GET | `/condominiums/{slug}/documents/{id}` | |
| GET | `/condominiums/{slug}/documents/{id}/file` | original PDF |
| GET | `/condominiums/{slug}/statement-entries` | `from`, `to`, `reconciliation`, `document_id` |
| POST | `/condominiums/{slug}/audit-runs` | `rules?: [CODE]` → **202** |
| GET | `/condominiums/{slug}/pipeline-runs/{uuid}` | job status, attempts, error, stats |
| GET | `/condominiums/{slug}/findings` | `status`, `severity`, `category`, `rule`, `include_inactive` |
| GET | `/condominiums/{slug}/findings/{id}` | with review history |
| PATCH | `/condominiums/{slug}/findings/{id}` | `status` (`open`/`confirmed`/`dismissed`), `note?` |

Roles: `viewer` reads; `auditor` and `owner` also upload, run audits and review.

## Example

```bash
TOKEN=$(curl -s localhost:8080/api/v1/auth/token \
  -d email=auditor@example.com -d password="$DEMO_USER_PASSWORD" -d device_name=cli | jq -r .token)

curl -s -H "Authorization: Bearer $TOKEN" \
  "localhost:8080/api/v1/condominiums/residencial-jardim-das-acacias/findings?severity=high" | jq '.data[].title'

curl -s -H "Authorization: Bearer $TOKEN" -F file=@statement.pdf -F type=financial_statement \
  -F reference_period=2025-11 localhost:8080/api/v1/condominiums/residencial-jardim-das-acacias/documents
```
