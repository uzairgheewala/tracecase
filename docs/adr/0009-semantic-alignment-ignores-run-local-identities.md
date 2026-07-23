# ADR 0009: Semantic alignment ignores run-local identities

## Decision

Execution comparison uses semantic signatures and constrained topology-aware matching. Trace IDs, span IDs, and ordinary workflow IDs are not primary alignment keys.

## Rationale

Those identifiers are regenerated per execution and would make equivalent runs appear unrelated. Stable domain identities may contribute as optional weighted evidence.
