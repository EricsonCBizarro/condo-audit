# ADR-0004 — Money is never a float

**Status:** accepted

## Decision

Amounts are `numeric(14,2)` in PostgreSQL and `decimal.Decimal` in Python,
parsed straight from text (`1.234,56` → `Decimal("1234.56")`). Laravel casts
them with `decimal:2`. Comparisons use an explicit half-cent tolerance.

## Why

The first prototype used floats and hit the classic bug: `Decimal("105.09") !=
105.09`, which silently dropped most non-round values when matching receipts.
An auditing tool cannot afford that. A property-based test (Hypothesis) checks
that formatting and parsing round-trip for any amount.
