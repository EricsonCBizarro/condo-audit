# ADR-0007 — Synthetic data with planted ground truth

**Status:** accepted

## Context

The project started on real documents, which cannot be published. A public
demo needs data that exercises the same paths (native PDFs, scans, receipts,
minutes) without a single real name or number.

## Decision

- `condo-audit synth generate --seed N` builds a fictional world
  deterministically (same seed, same bytes) and renders PDFs with ReportLab;
  some are rasterized with noise and rotation to force OCR.
- Every planted irregularity is written to `ground_truth.json`.
  `condo-audit eval` matches findings by rule, period and amount and reports
  precision and recall per rule. CI fails below 90%.
- A clean control condominium measures false positives.
- Tax ids are generated with invalid check digits on purpose (tested), so
  they can never belong to a real company.

## Consequences and limits

- 100% on this dataset is a **regression guarantee, not an accuracy claim**:
  the generator and the rules were written by the same people. The harness
  becomes more valuable as harder cases are added (noisier scans, other
  statement layouts) and when the AI agent is evaluated with it.
