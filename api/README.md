# api — Laravel 13

Product surface of condo-audit: Sanctum API (v1), Blade dashboard,
multi-tenancy (scoped bindings + policies), document ingestion, job dispatch
and the finding review workflow. It also owns the database schema.

| Path | What |
|---|---|
| `app/Documents/DocumentIngestionService.php` | hash → dedupe → store → record → enqueue |
| `app/Pipeline/` | `JobMessage` (contract), `PipelineDispatcher`, Redis queue |
| `app/Findings/FindingReviewService.php` | review state machine + audit trail |
| `app/Policies/CondominiumPolicy.php` | tenant boundary and roles |
| `app/Console/Commands/` | `demo:seed`, `audit:run` |
| `database/migrations/` | the whole schema |
| `tests/` | API, dashboard, tenancy, contract and command tests |

Inside the stack: `make test-api`, `make lint`. See [`../docs/api.md`](../docs/api.md).
