# Coverage and minimization

## Coverage subject

Coverage is always relative to a declared scenario-registry version. A report does not claim completeness over every possible distributed system. It reports which valid semantic points in that registry have witnesses.

## Point derivation

The engine derives expected points from families, topologies, axes, allowed faults, declared invariants, and observability profiles. It then merges witness records from deterministic scenario instances and optional analysis reports.

An interaction point has the form:

```text
family | fault-or-baseline | observability-profile
```

Only interactions allowed by the family registry are expected. Invalid Cartesian combinations are not mislabeled as uncovered.

## Recommendations

Recommendations group uncovered points by family and prioritize the families with the largest remaining coverage contribution. They may include a suggested fault and observability profile derived from an uncovered interaction.

## Minimization

`ScenarioMinimizer` removes parameters, fault applications, and expected-invariant declarations one at a time. A caller-supplied predicate decides whether the target violation or finding remains. Every attempted reduction is recorded with a candidate digest and preservation result.

This design allows the same minimizer to preserve:

- an invariant violation;
- a finding classification;
- a comparison divergence;
- a domain-specific Pathforge condition;
- a human-confirmed incident property.
