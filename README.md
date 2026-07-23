# Tracecase — Milestone D

Tracecase is an offline-first distributed-execution forensics toolkit. Milestone D adds privacy-safe disclosure and a concrete distributed reference laboratory above the portable case, graph, invariant, analyzer, and semantic-comparison layers delivered in Milestones A–C.

## Included capabilities

### Privacy classification and export policy

- Schema-aware field inventory across canonical cases.
- Internal, shareable, and public export profiles.
- Ordered retain, tokenize, digest, mask, truncate, remove, summarize, and reject actions.
- Stable keyed pseudonyms for equality-preserving correlation.
- Prohibited-pattern validation and canary-secret tests.
- Referential-integrity preservation.
- Redaction and export-validation artifacts inside the resulting bundle.
- Recomputed graph, timeline, invariants, and findings from sanitized evidence.

### Distributed reference laboratory

The initial lab binding realizes a browser → Django → PostgreSQL transaction → Celery worker → mock SIS/OCR → enrollment projection → audit → notification workflow.

It supports generic fault operators for:

- required-context loss;
- publish-before-commit ordering;
- duplicate durable effects;
- stale state;
- producer/consumer schema skew;
- broken observability linkage;
- prohibited sensitive capture;
- timeout after effect.

In-process mode is deterministic and drives tests, fixtures, CLI, API, and UI. A Docker Compose deployment provides the concrete Django/PostgreSQL/Redis/Celery realization.

### Workbench

The React Workbench now provides five investigation surfaces:

- **Explore Cases** — graph, timeline, semantics, invariants, findings, and evidence.
- **Construct Scenarios** — generic scenario generation.
- **Compare Executions** — semantic alignment and divergence.
- **Redact & Export** — field inventory, transformation preview, policy validation, and shareable export.
- **Live Lab** — run a baseline or faulted workflow, compare it, persist it, and inspect the resulting graph and findings.

## New repository areas

- `packages/tracecase-policy` — classification, deterministic transformation, validation, and shareable export.
- `packages/tracecase-lab` — generic-to-concrete lab bindings and in-process orchestration.
- `apps/reference-lab` — distributed Django/Celery/PostgreSQL/Redis/mock-SIS realization.
- `apps/api/privacy` — policy, inventory, preview, and export endpoints.
- `apps/api/lab` — binding, execution, comparison, and persistence endpoints.
- `registries/privacy` and `registries/lab` — exported policy and binding contracts.
- `fixtures/bundles/reference-lab-*` — internal, comparison, observability, privacy, and shareable portable cases.

## Validate

```bash
./scripts/validate.sh
```

Validation regenerates every milestone fixture, checks package boundaries, runs the complete Python suite, verifies directory and ZIP bundles, exercises invariant/analyzer/comparison/privacy/lab CLI commands, creates and verifies a temporary shareable export, compiles Python, and checks the Workbench TypeScript/TSX syntax. CI performs the full Vite production build.

## CLI examples

```bash
python -m tracecase_cli policy-list
python -m tracecase_cli privacy-inventory \
  fixtures/bundles/reference-lab-privacy-capture.tracecase
python -m tracecase_cli redaction-preview \
  fixtures/bundles/reference-lab-privacy-capture.tracecase
python -m tracecase_cli export-shareable \
  fixtures/bundles/reference-lab-privacy-capture.tracecase \
  /tmp/shareable.tracecase \
  --archive /tmp/shareable.tracecase.zip

python -m tracecase_cli lab-bindings
python -m tracecase_cli lab-run --seed 42 --fault fault.effect.duplicate.v1
python -m tracecase_cli lab-compare --seed 42 --fault fault.context.drop.v1
```

## Run the API and Workbench

```bash
python -m pip install -r apps/api/requirements.txt
python apps/api/manage.py runserver

cd apps/workbench
npm install
npm run dev
```

## Run the distributed laboratory

```bash
cd apps/reference-lab
docker compose up --build
```

The `.tracecase` bundle remains the evidence source of truth. Django indexes and serves bundles, while the privacy engine creates a separately identified sanitized derivative rather than mutating the source case.
