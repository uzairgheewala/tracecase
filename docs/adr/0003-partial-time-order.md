# ADR 0003: Time is represented as observations and typed relations

**Status:** Accepted

## Decision

Tracecase does not assume one globally authoritative clock. Every timestamp records clock identity, precision, uncertainty, and normalization method. Ordering belongs in explicit or derived typed relations rather than file order.

## Consequences

- Future graph assembly can preserve concurrency and clock contradictions.
- The Workbench cannot imply false chronological precision.
- Adapters must retain source-clock provenance.
