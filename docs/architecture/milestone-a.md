# Milestone A architecture

Milestone A establishes a portable and independently verifiable case representation before collection, correlation, invariant evaluation, or comparison logic exists.

## Layering

```text
Source-native evidence (future adapters)
        ↓
Canonical observations and provenance
        ↓
Execution nodes, relations, context, state, effects
        ↓
ExecutionCase
        ↓
.tracecase bundle
        ↓
Django API index / React Workbench
```

The Workbench and API may project bundle content, but neither owns the evidence.

## Dependency rules

- `tracecase-model` depends only on Pydantic and the Python standard library.
- `tracecase-bundle` depends on `tracecase-model`.
- `tracecase-cli` depends on the model and bundle packages.
- Django depends inward on the packages.
- React depends on the HTTP projection, never on Python implementation details.
- Future collectors and analyzers depend on the canonical model, not vice versa.

## Milestone boundary

Included:

- semantic contracts;
- reference integrity;
- canonical serialization;
- portable bundle construction;
- checksums and freeze verification;
- sample execution fixture;
- read-only API and Workbench.

Deferred:

- scenario registry and generation;
- real telemetry adapters;
- correlation and inferred graph assembly;
- invariant evaluation;
- analyzers and findings;
- semantic comparison;
- redaction and shareable export policies.
