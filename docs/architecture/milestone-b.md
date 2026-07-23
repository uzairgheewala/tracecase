# Milestone B architecture

Milestone B implements Phases 4–8 of the Tracecase roadmap. Its boundary is a complete path from a generic scenario-family declaration to a portable observed execution and deterministic reconstructed graph.

```text
Scenario registry
      ↓
Scenario definition and bindings
      ↓
Deterministic instance generator
      ↓
Synthetic ground-truth execution
      ↓ semantic fault operators
Faulted ground truth
      ↓ observability profile and evidence operators
Observed execution case
      ↓ bundle supplements or source adapters
Canonical fragments
      ↓ graph assembler
Derived graph, identity groups, context flows, effect groups and timeline
      ↓
Workbench and CLI
```

## Package boundaries

### `tracecase-scenarios`

Owns semantic universes, topology motifs, scenario families, fault operators, deterministic generation and synthetic realization. It depends only on `tracecase-model`.

### `tracecase-collectors`

Owns source-adapter contracts, candidate discovery, collection coordination, provenance-preserving normalization and collection diagnostics. It depends only on `tracecase-model`.

### `tracecase-graph`

Owns deterministic graph assembly and timeline projection from canonical evidence. It depends only on `tracecase-model`.

### `tracecase-bundle`

Remains unaware of scenario and graph types. Milestone B stores them as schema-addressed supplemental artifacts, preserving a one-way dependency graph.

## Ground truth and observed evidence

Synthetic generation produces two cases:

1. **Ground-truth case:** the execution after semantic faults have changed what actually happened.
2. **Observed case:** the available evidence after missing spans, broken links, sampling, clock skew, contradiction or redaction has changed what can be known.

An absent observation never automatically means that an operation failed to happen. This separation is required for later inconclusive invariant results and instrumentation-quality analysis.

## Derived graph contract

The assembler does not replace source relationships. It emits additional relations and projections with a declared derivation class and supporting evidence. Consumers can therefore distinguish:

- explicit application relations;
- source-native telemetry relations;
- deterministic relations derived from stable identities;
- heuristic candidate relations.

## Milestone boundary

Milestone B intentionally does not yet interpret the graph into violations or findings. Generic invariant evaluation, analyzer families and semantic execution comparison begin in Milestone C.
