# Scenario registry contract

The scenario registry defines the bounded semantic universe supported by one Tracecase release. It is a portable declarative catalog, not an application-specific incident list.

## Registry contents

A registry contains:

- semantic-universe declarations;
- topology motifs;
- parameter domains;
- generic invariant references;
- fault-operator definitions;
- scenario families;
- compatibility and registry metadata.

Generated JSON snapshots live under `registries/` and are produced from the typed Python registry definitions.

## Scenario family

A family declares:

- a stable family ID and version;
- semantic class;
- topology template;
- parameters and admissibility rules;
- allowed fault operators;
- expected invariants;
- supported observability profiles;
- minimization hints and coverage dimensions.

Families identify mechanisms such as required-context disappearance or duplicate durable effects. They do not name Django, Celery, HTTP route strings, student records or Pathforge models.

## Scenario definition and instance

A definition binds a family to a selected topology and optionally constrains parameter domains. An instance is a fully resolved, immutable realization with:

- concrete values;
- random seed;
- selected faults and targets;
- observability profile;
- expected outcomes;
- coverage points;
- deterministic instance digest.

The same definition and seed must always generate the same instance.

## Fault classes

Fault operators are classified as:

- **semantic:** modify the actual execution, state or effect behavior;
- **observability:** modify only the evidence available to an investigator.

This classification is enforced by the synthetic engine rather than left to naming conventions.

## Coverage modes

The generator supports:

- one exact instance;
- deterministic random sampling;
- constrained exhaustive generation for bounded domains;
- pairwise covering sets.

Invalid combinations are rejected through explicit admissibility constraints. Coverage reports must distinguish unsupported, inadmissible, uncovered and covered points.
