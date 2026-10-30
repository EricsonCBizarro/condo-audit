# ADR-0005 — Tesseract by default, OCR behind an interface

**Status:** accepted

## Context

The first prototype used PaddleOCR, which was noticeably better on dense,
low-quality tables but pulls several gigabytes of dependencies and models.
That conflicts with "clone and run in five minutes".

## Decision

- Read the native text layer first (PyMuPDF). Only pages without one are
  rendered at 300 DPI and OCR'd.
- Default engine: **Tesseract 5** with Portuguese data, from Ubuntu packages.
- Engines implement a one-method `OcrEngine` protocol returning positioned
  words with a confidence, so PaddleOCR or a cloud OCR can be plugged in
  without touching extraction.
- Low OCR confidence never produces an accusation: a broken balance on a
  low-confidence line becomes a `data_quality` review item (ADR-0006).

## Consequences

Small image, fast start, good accuracy on reasonably clean scans. Harder
scans may need a stronger engine; the protocol keeps that a local change.
