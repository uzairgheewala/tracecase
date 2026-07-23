# Canonical execution model v1

## Aggregate

`ExecutionCase` contains:

1. `CaseSpecification` — why and how the case exists;
2. `SystemModel` — components, boundaries, and resources;
3. `CaseEvidence` — sources and one canonical `ExecutionModel`;
4. `CaseInterpretations` — empty or additive derived interpretation layer;
5. lifecycle and schema version.

## Execution model

`ExecutionModel` is a typed graph plus non-control-flow semantics:

- nodes;
- typed relations;
- multi-dimensional identities;
- context fields and propagation contracts;
- state facts;
- durable or ambiguous effects;
- observations and provenance.

All IDs are globally unique within an execution model. References are validated at model construction. Relations may point to nodes, facts, effects, or observations. Technology-specific detail is preserved only in namespaced extensions.

## Evidence separation

An `Observation` represents source evidence. A node, state fact, or effect is a normalized semantic record. Later invariant results and findings will remain separate derived artifacts. The schema does not permit a finding to masquerade as recorded evidence.
