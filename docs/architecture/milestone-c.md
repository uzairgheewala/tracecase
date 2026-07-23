# Milestone C architecture

Milestone C implements the trusted interpretation and comparison layers above frozen Tracecase evidence.

## Dependency direction

```text
tracecase-model + tracecase-graph
             ↓
tracecase-invariants
             ↓
tracecase-analyzers

tracecase-model + tracecase-graph
             ↓
tracecase-compare
```

The comparison package intentionally does not depend on the invariant or analyzer packages. It compares canonical executions directly; downstream products may correlate divergences with findings without making alignment depend on a particular analyzer pack.

## Trusted layers

1. Source evidence and canonical records.
2. Additive derived execution graph.
3. Deterministic invariant evaluations.
4. Bounded findings that cite invariant results and evidence.
5. Semantic alignments and divergences between frozen cases.

No layer mutates a lower layer. Every result declares producer version, evidence classification, confidence, supporting references, and limitations.

## Milestone boundary

Milestone C deliberately excludes privacy transformation, live fault-lab execution, coverage optimization, and Pathforge-specific semantics. Those remain later milestones.
