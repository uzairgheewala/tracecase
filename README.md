# Tracecase — Milestone C

Tracecase is an offline-first distributed-execution forensics toolkit. Milestone C adds deterministic contract evaluation, bounded evidence-linked findings, and semantic success-versus-failure comparison above the portable case and reconstructed execution graph delivered in Milestones A and B.

## Included capabilities

### Generic invariant runtime

- Versioned, declarative invariant registry.
- Safety, liveness, continuity, isolation, ordering, compatibility, resource, observability, and privacy contracts.
- Satisfied, violated, inconclusive, contradicted, not-applicable, and evaluation-error outcomes.
- Evidence requirements, minimal counterexamples, confidence, and deterministic evaluation traces.

### Bounded analyzer packs

- Context continuity.
- Identity integrity.
- Retry and durable-effect behavior.
- Transaction ordering.
- Observability integrity.
- Resource and work amplification.
- Contract and privacy signals.

Every finding cites canonical evidence and exposes its limitations.

### Semantic execution comparison

- Aligns operations by semantic role and structure rather than regenerated trace IDs.
- Handles retries, optional branches, unmatched nodes, and ambiguous candidates.
- Classifies structural, context, identity, timing, state, effect, error, resource, deployment, and evidence divergences.
- Selects the first consequential, evidence-grounded divergence.

### Workbench

The React Workbench now supports:

- case exploration with invariant and finding panels;
- evidence-linked finding inspection;
- baseline/candidate selection;
- synchronized semantic operation alignment;
- divergence navigation;
- first meaningful divergence presentation.

## Repository layout

- `packages/tracecase-invariants` — invariant definitions and runtime.
- `packages/tracecase-analyzers` — analyzer registry and bounded findings.
- `packages/tracecase-compare` — semantic alignment and divergence engine.
- `apps/api/comparisons` — comparison API.
- `apps/workbench` — investigator and comparison UI.
- `fixtures/bundles/*analysis*` — analyzed portable cases.
- `fixtures/bundles/semantic-context-comparison.tracecase` — portable comparison profile.

## Validate

```bash
./scripts/validate.sh
```

The validation command regenerates all fixtures, checks architecture boundaries, runs the Python suite, verifies directory and archive bundles, exercises invariant/analyzer/comparison CLI commands, compiles Python, and checks the Workbench source when dependencies are available.

## CLI examples

```bash
python -m tracecase_cli invariants fixtures/bundles/context-analysis-failure.tracecase
python -m tracecase_cli analyze fixtures/bundles/duplicate-effect-analysis.tracecase
python -m tracecase_cli compare \
  fixtures/bundles/context-analysis-baseline.tracecase \
  fixtures/bundles/context-analysis-failure.tracecase
```

## Run the API and Workbench

```bash
python -m pip install -r apps/api/requirements.txt
python apps/api/manage.py runserver

cd apps/workbench
npm install
npm run dev
```

The `.tracecase` bundle remains the evidence source of truth. Django indexes and serves cases; the database does not replace portable evidence.
