# ADR 0005: Derived graph assembly is additive

## Status

Accepted for Milestone B.

## Context

Source telemetry may provide incomplete or contradictory relationships. Rewriting source edges during correlation would erase provenance and make reconstruction impossible to audit.

## Decision

Graph assembly preserves all canonical nodes and source relations, then emits additional typed relations and projections. Every derived relation declares its derivation class, supporting evidence and confidence where applicable.

## Consequences

- Investigators can compare source and reconstructed topology.
- Reanalysis is deterministic and auditable.
- Consumers must choose which derivation classes to display or trust.
- Later analyzers can report contradictions instead of receiving sanitized input.
