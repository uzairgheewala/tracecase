# Declarative invariant runtime

The invariant runtime evaluates versioned, framework-neutral contracts over an `ExecutionCase` and its additive `AssembledExecutionGraph`.

## Result algebra

An evaluation returns one of:

- `satisfied`
- `violated`
- `inconclusive`
- `contradicted`
- `not_applicable`
- `evaluation_error`

Missing evidence never silently becomes success or failure. Each result records its scope, evidence requirements, confidence, evidence classification, counterexample references, missing evidence, and deterministic evaluation trace.

## Initial invariant pack

The built-in registry covers context continuity and forbidden propagation, identity isolation and workflow correlatability, at-most-once and eventual effects, read-after-visibility, freshness, schema compatibility, capacity, work amplification, required causal linkage, and prohibited capture.

## Genericism

Evaluators operate on canonical node, relation, context, state, effect, and observation semantics. Django, Celery, OpenTelemetry, and application-specific extensions may enrich those records but are not required by the runtime.
