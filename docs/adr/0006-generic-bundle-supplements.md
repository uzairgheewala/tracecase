# ADR 0006: Store milestone extensions as generic bundle supplements

## Status

Accepted for Milestone B.

## Context

Scenario, collection and graph packages evolve independently from the portable bundle implementation. Importing those packages into `tracecase-bundle` would reverse the intended dependency direction.

## Decision

The bundle builder accepts schema-addressed supplemental artifacts. Supplements declare path, media type, schema reference, integrity scope and deterministic metadata. The bundle package serializes them without importing their domain models.

## Consequences

- The bundle contract remains extensible and package-independent.
- Unknown future artifacts can survive round trips.
- Each producer is responsible for validating its artifact before handing it to the bundle layer.
- Bundle-level integrity still covers every supplemental file.
