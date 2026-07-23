# ADR 0004: Separate ground truth from observed evidence

## Status

Accepted for Milestone B.

## Context

Synthetic scenarios need to model both failures in the system and failures in instrumentation. Treating dropped evidence as a missing operation would make analyzers incapable of distinguishing product defects from observability defects.

## Decision

The synthetic engine creates a ground-truth case after semantic faults, then independently derives an observed case through observability faults and profiles. Both are optionally retained in reproducible synthetic bundles.

## Consequences

- Missing evidence can later yield `inconclusive` rather than false violations.
- Observability analyzers can be tested against known ground truth.
- Synthetic bundle size is larger when both layers are retained.
- Natural production cases normally contain only observed evidence and therefore cannot claim hidden ground truth.
