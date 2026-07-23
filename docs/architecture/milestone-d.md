# Milestone D architecture

Milestone D adds the controlled disclosure boundary and the first concrete distributed realization of Tracecase's generic execution semantics.

## Privacy plane

The privacy plane is split into four deterministic stages:

1. **Inventory** walks the canonical case and labels fields by schema position, declared sensitivity and key/path policy.
2. **Transformation** applies an ordered export policy without changing canonical identifiers or reference targets.
3. **Re-analysis** rebuilds graph, timeline, invariants and findings from the sanitized evidence rather than copying potentially sensitive derived artifacts.
4. **Validation** scans the transformed case, policy artifacts and integrity result before a bundle can carry the `shareable` profile.

This preserves a strict distinction between a source bundle and a disclosed derivative. A shareable case receives a new case identity and references its policy in the case specification and manifest.

## Reference laboratory

The reference laboratory has two realizations behind one binding:

- `in_process` deterministically constructs and evaluates a real-shaped execution for tests, fixtures and the Workbench.
- `distributed` launches the Django, PostgreSQL, Redis/Celery and mock-SIS deployment under `apps/reference-lab`.

The binding maps a concrete transcript-import workflow onto generic semantic roles. Fault references stay generic and are interpreted by the binding at explicit lifecycle points. The canonical model and analyzers therefore never import the reference application.

## Dependency direction

```text
reference application / UI / API
              ↓
tracecase-lab       tracecase-policy
       ↓                    ↓
collectors / graph / invariants / analyzers / compare
                         ↓
                  canonical model
                         ↓
                   bundle contract
```

`tracecase-policy` may rebuild derived artifacts but does not mutate source evidence in place. `tracecase-lab` produces ordinary `ExecutionCase` values; downstream systems do not receive a special lab-only case model.

## Trust boundaries

- Runtime credentials and connector configuration remain outside bundles.
- Unknown supplements are omitted from shareable exports unless explicitly classified safe.
- Stable tokens are scoped by the selected key and preserve equality only where policy permits.
- Fault injection is isolated to the reference laboratory and disabled in ordinary application code.
- Distributed mode is opt-in and uses a dedicated compose deployment and database.
