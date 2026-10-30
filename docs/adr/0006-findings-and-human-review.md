# ADR-0006 — Evidence-first findings, stable fingerprints, humans decide

**Status:** accepted

## Decision

- A rule is a pure function of a typed `AuditContext`; it returns
  `FindingDraft`s with a severity, an explanation and **evidence**: document,
  page and the exact excerpt (statement line, receipt fields, the convention
  article, the minutes item).
- Every finding has a fingerprint = hash(rule code + subject). Re-running the
  audit upserts by fingerprint: no duplicates, and a human review
  (`confirmed`/`dismissed`, with a note and an audit trail in
  `finding_events`) is never reset. Findings the latest run no longer
  produces are marked inactive, not deleted.
- Two categories: `irregularity` (the money or the rules do not add up) and
  `data_quality` (the tool is not sure what it read). Only the first counts
  as a finding in the evaluation.
- Derived rows that people interact with (statement entries, receipts, links)
  are upserted by natural key on reprocessing, so their ids, and confirmed or
  rejected links, survive.

## Why

The tool's output may end up in front of a property manager or a court. It
must show its work, never silently change a reviewed decision, and never turn
an OCR glitch into an accusation. Evidence with page references is also what
the AI phase needs for citation-grounded answers.
