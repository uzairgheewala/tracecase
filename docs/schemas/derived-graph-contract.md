# Derived execution graph contract

The derived graph is a reproducible projection over a frozen canonical execution case. It is not evidence and does not modify evidence.

## Graph artifacts

An assembled graph contains:

- source execution nodes;
- source relations;
- derived relations;
- identity groups;
- context-flow records;
- effect groups;
- temporal constraints;
- disconnected components;
- warnings and completeness metadata.

A timeline projection contains ordered lanes and timeline entries while preserving uncertainty and explicit temporal constraints.

## Relation derivations

Derived relations carry a derivation class:

- `explicit`;
- `source_native`;
- `deterministic`;
- `heuristic`;
- `human_asserted`.

A deterministic relation must identify the identity or rule that produced it. A heuristic relation must declare confidence and must never be rendered as equivalent to an explicit edge.

## Initial deterministic derivations

Milestone B derives relations for:

- parent-span ancestry;
- workflow and logical-operation grouping;
- task-attempt and retry lineage;
- message publish/consume linkage;
- repeated logical effects;
- context continuity across topology paths;
- temporal order implied by source relations and timestamps.

## Timeline semantics

Array order is never treated as causal order. Timeline entries expose normalized times, durations, component lanes and uncertainty. Contradictions and disconnected fragments are retained for later analyzers rather than silently repaired.

## Bundle representation

Graph and timeline artifacts are written as generic supplemental bundle files with declared media type, schema reference, integrity scope and deterministic producer metadata. Their source evidence digest allows consumers to detect stale derived artifacts.
