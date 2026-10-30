# ADR-0001 — Two services: Laravel for the product, Python for documents

**Status:** accepted

## Context

The system has two very different kinds of work:

- a product surface — authentication, tenancy, uploads, a REST API, a review
  workflow and a dashboard;
- document processing — PDF parsing, OCR, layout analysis, extraction and a
  rules engine, and soon embeddings, RAG and an agent.

## Decision

Keep two services with a hard boundary:

- `api/` (PHP 8.3, Laravel 13) owns the product surface **and the database
  schema** (migrations).
- `pipeline/` (Python 3.12) owns everything that reads documents and judges
  them.

They share PostgreSQL and talk through a versioned job contract on Redis
(ADR-0002).

## Consequences

- Each side uses the strongest ecosystem for its job: Laravel's auth,
  validation, policies and Blade; Python's PDF/OCR libraries and, later, the
  AI stack.
- One schema owner avoids two migration systems fighting each other. The
  pipeline writes rows but never alters tables.
- Cost: two toolchains, two test suites, two CI jobs. The contract and its
  tests on both sides keep the seam honest.

## Alternatives considered

- **Everything in Python (FastAPI + a templating layer):** one language, but a
  weaker product layer (auth, policies, admin UI) to rebuild by hand.
- **Everything in PHP:** OCR and document tooling in PHP is thin; the AI phase
  would be fighting the ecosystem.
- **Laravel calling Python as a subprocess** (what the first prototype did):
  simple on one machine, but it couples deployment, file paths and failure
  modes, and it does not scale out.
