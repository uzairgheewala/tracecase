# ADR 0007: Invariant results are multi-valued

## Decision

Invariant evaluation uses satisfied, violated, inconclusive, contradicted, not-applicable, and evaluation-error states rather than Boolean output.

## Rationale

Distributed evidence is routinely partial or conflicting. Boolean collapse would convert telemetry absence into false certainty and make observability failures indistinguishable from product failures.
