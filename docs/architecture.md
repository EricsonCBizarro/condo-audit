# Architecture

## Services

```mermaid
flowchart LR
    subgraph clients[Clients]
        B[Browser · dashboard]
        C[API client / CLI]
    end
    subgraph api[api · Laravel 13]
        H[HTTP API v1 + Blade dashboard]
        I[DocumentIngestionService]
        D[PipelineDispatcher]
        R[FindingReviewService]
    end
    subgraph pipeline[pipeline · Python 3.12]
        W[Worker · reliable queue]
        P[DocumentProcessor]
        A[AuditRunner · 10 rules]
    end
    S3[(S3 bucket<br/>SeaweedFS locally)]
    PG[(PostgreSQL 16<br/>+ pgvector)]
    Q[[Redis<br/>jobs · delayed · dead]]

    B & C --> H
    H --> I --> S3
    I --> D
    D -- 1. insert pipeline_runs --> PG
    D -- 2. RPUSH job JSON --> Q
    H --> R --> PG
    Q -- BLMOVE --> W
    W --> P & A
    P -- read original --> S3
    P -- pages, lines, entities --> PG
    A -- findings --> PG
```

## One upload, end to end

```mermaid
sequenceDiagram
    autonumber
    participant U as User
    participant API as Laravel API
    participant S3 as Object storage
    participant PG as PostgreSQL
    participant Q as Redis
    participant W as Python worker

    U->>API: POST /documents (PDF) + X-Correlation-Id
    API->>API: SHA-256, dedupe per condominium
    API->>S3: put original (bronze)
    API->>PG: documents row + pipeline_runs (queued)
    API->>Q: RPUSH job {document.process}
    API-->>U: 202 Accepted + run id
    W->>Q: BLMOVE jobs → processing:<worker>
    W->>PG: run → running
    W->>S3: get original
    W->>W: native text or OCR → lines → page types → extraction
    W->>PG: one transaction: pages, lines, entries, receipts, links
    W->>PG: run → succeeded (stats)
    W->>Q: LREM processing (ack)
    U->>API: POST /audit-runs
    W->>PG: load AuditContext → rules → upsert findings by fingerprint
```

## Data layers

| Layer | What | Tables / storage | Rule |
|---|---|---|---|
| Bronze | original file, SHA-256, ingestion time | bucket + `documents` | never edited |
| Silver | text per page, lines with bbox and confidence, page type | `document_pages`, `page_lines` | rebuilt on reprocessing |
| Gold | statement entries, receipts, budget, agenda, decisions, clauses, parameters, penalties | domain tables | upserted by natural key |
| Findings | rule results with evidence | `findings`, `finding_events` | upserted by fingerprint; reviews never reset |

## Pipeline stages

1. **Text.** PyMuPDF words for pages with a text layer; otherwise the page is
   rendered at 300 DPI and read by Tesseract (`por`). Both produce positioned
   words with a confidence ([`documents/reader.py`](../pipeline/src/condo_audit/documents/reader.py)).
2. **Layout.** Words → lines. Statement tables are split at the midpoints
   between dates of the left-most date column, which survives uneven row
   spacing and slightly rotated scans ([`layout.py`](../pipeline/src/condo_audit/documents/layout.py)).
3. **Page type.** `statement`, `receipt`, `contract`, `other`, by token
   co-occurrence that tolerates OCR noise ([`pages.py`](../pipeline/src/condo_audit/extraction/pages.py)).
4. **Extraction.** One extractor per document type: statement rows with
   balance reconciliation, receipts, budget lines, agenda items, decisions
   (approved? amount?), bylaw clauses and the penalty ladder, the convention's
   spending limit, penalty notices.
5. **Linking.** Debits ↔ receipts by amount, payee words and date
   ([`linking.py`](../pipeline/src/condo_audit/linking.py)). Suggestions only;
   confirmed or rejected links are never touched.
6. **Audit.** Pure rules over a typed context ([`audit/`](../pipeline/src/condo_audit/audit/)).

## Reliability

- **At-least-once jobs, idempotent handlers.** Reprocessing a document or
  re-running an audit converges to the same rows.
- **Retries with backoff** (`5s · 2^attempt`), **dead-letter list** after
  3 attempts, **orphan recovery** via worker heartbeats.
- **Tenant checks twice:** scoped route bindings + policies in the API; the
  worker refuses a document that does not belong to the job's condominium.
- **Health:** `GET /api/v1/health` checks PostgreSQL, Redis and the bucket.
- **Tracing:** one correlation id per request, logged by both services.

## Decisions

See [`adr/`](adr/) for the reasoning behind each choice and its trade-offs.
