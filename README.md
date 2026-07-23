# Tracecase — Milestone E

Tracecase is an offline-first distributed-execution forensics toolkit. Milestone E completes the initial roadmap by adding semantic coverage and counterexample minimization, bundle compatibility and hardening, public instrumentation/plugin surfaces, and an isolated Pathforge integration.

## Milestone E capabilities

### Coverage Observatory

`tracecase-coverage` builds a coverage ledger relative to a versioned scenario universe. It measures:

- scenario families;
- semantic-universe axes;
- topology motifs;
- fault operators;
- invariants;
- observability profiles;
- valid family/fault/profile interactions;
- invariant outcomes;
- synthetic and concrete realizations.

The generated fixture currently contains 108 valid points: 83 covered and 25 uncovered. Recommendations identify the next families and configurations with the greatest marginal coverage value.

The deterministic minimizer accepts an external preservation oracle and records each reduction. The seeded witness reduces from three input elements to one while preserving the required-context violation.

### Compatibility and hardening

`tracecase-compat` adds:

- explicit compatible, migratable, incompatible, and unknown results;
- a seeded lossless `0.9.0 → 1.0.0` manifest migration;
- integrity and JSONL health scanning;
- recovery recommendations;
- namespaced-extension preservation;
- component, operation, identity, effect, and neighborhood indexes;
- bounded JSONL paging;
- ZIP entry-count, size, path, and compression-ratio limits.

### Public SDK and plugin contracts

`tracecase-sdk` provides:

- context propagation through Python `contextvars`;
- operation start/end and error recording;
- domain-event and effect recording;
- in-memory and JSONL event sinks;
- adapter and analyzer plugin protocols;
- duplicate-safe plugin registration.

It depends only on the canonical model and is suitable for framework-specific integrations without introducing those frameworks into the core.

### Pathforge integration

`tracecase-pathforge` is an isolated edge package. It contributes:

- requirement-audit and reconciliation bindings;
- `pathforge.academic` extension schemas;
- Pathforge workflow/run contexts;
- domain-event bridging;
- portable baseline, fault, and comparison cases;
- URL-addressable Workbench deep links.

The baseline requirement-audit run uses the ordinary generic Tracecase graph, invariant, analyzer, and comparison engines. The tenant-loss comparison aligns all five operations and selects the solver boundary at 90 ms as the first meaningful divergence.

### Workbench

The Workbench now provides eight surfaces:

- Explore Cases
- Construct Scenarios
- Compare Executions
- Redact & Export
- Live Lab
- Coverage Observatory
- Compatibility & Health Center
- Pathforge Integration

## New repository areas

- `packages/tracecase-coverage`
- `packages/tracecase-compat`
- `packages/tracecase-sdk`
- `packages/tracecase-pathforge`
- `apps/api/coveragecenter`
- `apps/api/healthcenter`
- `apps/api/pathforge`
- `docs/coverage`
- `docs/compatibility`
- `docs/sdk`
- `docs/pathforge`
- `registries/coverage`
- `registries/compatibility`
- `registries/sdk`
- `registries/pathforge`

## Validate

```bash
./scripts/validate.sh
```

The suite regenerates Milestones A–E fixtures, enforces package boundaries, runs all Python tests, verifies directory and ZIP bundles, exercises the old and new CLI surfaces, compiles Python, and checks Workbench TypeScript/TSX syntax. CI performs the complete Vite production build.

## New CLI examples

```bash
python -m tracecase_cli coverage-report

python -m tracecase_cli bundle-compat \
  fixtures/bundles/pathforge-audit-baseline.tracecase
python -m tracecase_cli bundle-health \
  fixtures/bundles/pathforge-audit-baseline.tracecase
python -m tracecase_cli neighborhood \
  fixtures/bundles/pathforge-audit-baseline.tracecase \
  node.pathforge.request --depth 2

python -m tracecase_cli pathforge-bindings
python -m tracecase_cli pathforge-run --seed 42
python -m tracecase_cli pathforge-compare --seed 42 --fault tenant-loss
```

## Run the API and Workbench

```bash
python -m pip install -r apps/api/requirements.txt
python apps/api/manage.py runserver

cd apps/workbench
npm install
npm run dev
```

The `.tracecase` bundle remains the evidence source of truth. Coverage, compatibility, health, Pathforge, and UI artifacts remain integrity-covered supplements or reproducible projections over frozen evidence.
