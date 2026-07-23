# Tracecase — Milestone B

Tracecase is an offline-first distributed-execution forensics toolkit. Milestone B extends the portable evidence foundation from Milestone A with a generic scenario algebra, deterministic scenario generation, synthetic ground-truth and observed-evidence production, source-adapter contracts, and deterministic execution-graph assembly.

## Implemented milestones

### Milestone A — Portable execution case

- **Phase 0:** monorepo, dependency rules, CI, API and Workbench foundations.
- **Phase 1:** canonical primitives, provenance, time, sensitivity and schema catalog.
- **Phase 2:** framework-neutral execution model for nodes, relations, identity, context, state, effects and observations.
- **Phase 3:** portable `.tracecase` bundles, canonical serialization, content indexes, digests, freeze semantics and verification.

### Milestone B — Scenario-to-execution reconstruction

- **Phase 4:** semantic universes, topology motifs, invariant references, generic scenario families and fault-operator registries.
- **Phase 5:** deterministic scenario definitions, constrained instance generation and pairwise coverage generation.
- **Phase 6:** synthetic execution engine with separate ground-truth and observed-evidence layers.
- **Phase 7:** generic adapter and collection framework, OpenTelemetry JSON adapter, structured-event adapter and tenant-scope enforcement.
- **Phase 8:** deterministic execution-graph assembly, identity groups, context flows, effect groups, partial temporal order and timeline projections.

The `.tracecase` bundle remains the source of truth. Django indexes and serves bundles but is not required to inspect, verify or reconstruct them.

## Repository layout

```text
packages/tracecase-model/       Canonical semantic contracts
packages/tracecase-bundle/      Portable bundle implementation
packages/tracecase-scenarios/   Semantic universes, families and generation
packages/tracecase-collectors/  Source-adapter and collection framework
packages/tracecase-graph/       Correlation, derived graph and timeline
packages/tracecase-cli/         Command-line interface
apps/api/                        Django/DRF local control plane
apps/workbench/                  React/TypeScript investigator and scenario UI
registries/                      Generated portable registry snapshots
fixtures/bundles/                Milestone A and B conformance bundles
tests/                           Unit, conformance and integration tests
scripts/                         Validation and fixture generation
```

## Quick validation

Requires Python 3.11+ and Pydantic 2:

```bash
./scripts/validate.sh
```

The script checks architectural dependencies, regenerates all fixtures, runs the test suite, verifies every bundle, exercises scenario and graph CLI commands, and compiles all Python sources.

## CLI examples

Set the local source packages on `PYTHONPATH` when running without installing them:

```bash
export PYTHONPATH="packages/tracecase-model/src:packages/tracecase-bundle/src:packages/tracecase-scenarios/src:packages/tracecase-collectors/src:packages/tracecase-graph/src:packages/tracecase-cli/src"
```

List generic scenario families:

```bash
python -m tracecase_cli scenario-list
```

Generate a deterministic scenario instance:

```bash
python -m tracecase_cli scenario-generate \
  continuity.context_disappearance.v1 \
  --seed 42 \
  --fault fault.context.drop.v1 \
  --target consumer
```

Verify and summarize a generated bundle:

```bash
python -m tracecase_cli verify \
  fixtures/bundles/context-continuity-failure.tracecase

python -m tracecase_cli graph-summary \
  fixtures/bundles/context-continuity-failure.tracecase
```

## Django API

Install the dependencies in `apps/api/requirements.txt`, then:

```bash
cd apps/api
python manage.py runserver
```

The API discovers bundles beneath `TRACECASE_BUNDLE_ROOT`, defaulting to `fixtures/bundles`. Milestone B adds assembled graph, timeline and scenario-generation endpoints.

## React Workbench

```bash
cd apps/workbench
npm ci
npm run dev
```

Set `VITE_TRACECASE_API_BASE` when the API is not served from `http://localhost:8000/api`.

The Workbench now has two functional modes:

- **Explore Cases:** graph, timeline, identity groups, context flows, effect groups, oracle outcomes and evidence inspection.
- **Construct Scenarios:** choose a generic family, bind parameters, apply a semantic or observability fault and generate an execution through the API.

## Architectural constraints

1. Core semantic packages never import Django, Celery, OpenTelemetry, React or Pathforge.
2. Scenario families describe invariant mechanisms and topology roles rather than named frameworks.
3. Semantic faults modify ground truth; observability faults modify only available evidence.
4. Adapters normalize source records into canonical fragments and preserve provenance.
5. Graph assembly derives relationships without mutating source evidence.
6. Explicit, source-native, deterministic and heuristic relationships remain distinguishable.
7. Bundle supplements are generic artifacts; the bundle package does not import scenario or graph packages.
8. Frozen bundle payloads are independently checksum-verifiable.
