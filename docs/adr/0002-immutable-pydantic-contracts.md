# ADR 0002: Canonical contracts use immutable Pydantic models

**Status:** Accepted

## Decision

Core semantic records are frozen Pydantic v2 models with forbidden unknown core fields and explicit namespaced extension maps.

## Consequences

- Validation and JSON Schema generation share one contract.
- Canonical records cannot be accidentally mutated in memory.
- Unknown unnamespaced fields fail fast.
- Technology-specific fields survive through controlled extensions.
