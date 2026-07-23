# ADR 0011: Recompute derived artifacts after redaction

## Status

Accepted.

## Decision

Shareable exports do not copy source graph, invariant, finding or report artifacts. They rebuild them from sanitized canonical evidence and copy only explicitly allowlisted supplements.

## Consequences

Derived artifacts cannot leak removed source values. Export is slower but deterministic, auditable and semantically consistent with disclosed evidence.
