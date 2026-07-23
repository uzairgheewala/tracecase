# ADR 0001: File-backed case bundles are the source of truth

**Status:** Accepted

## Decision

Canonical case evidence is stored in portable `.tracecase` bundles. The Django database may index bundles and store mutable workspace state but cannot be the exclusive evidence store.

## Consequences

- Cases remain inspectable offline.
- Integrity can be checked independently of the originating service.
- Server persistence can evolve without changing the bundle contract.
- Large-case indexing and caching remain implementation concerns rather than semantic requirements.
