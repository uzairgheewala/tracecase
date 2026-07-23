# Tracecase — Milestone A

Milestone A implements the portable-case foundation for Tracecase:

- **Phase 0:** monorepo, dependency rules, validation scripts, API/UI shells;
- **Phase 1:** canonical primitives, time, provenance, sensitivity, schema catalog;
- **Phase 2:** framework-neutral execution model covering nodes, relations, identity, context, state, effects, observations, systems, and cases;
- **Phase 3:** `.tracecase` bundle manifests, deterministic JSON/JSONL, content indexing, checksums, freeze semantics, verification, packing, and inspection.

The `.tracecase` bundle is the source of truth. The Django API is a file-backed index and delivery layer; it is not required to inspect or verify a case.

## Repository layout

```text
packages/tracecase-model/   Canonical semantic contracts
packages/tracecase-bundle/  Portable bundle implementation
packages/tracecase-cli/     Command-line interface
apps/api/                    Django/DRF file-backed API
apps/workbench/              React/TypeScript bundle explorer
fixtures/bundles/            Generated conformance fixtures
tests/                       Core and bundle tests
scripts/                     Validation and fixture generation
```

## Quick validation

The core and bundle tests require Python 3.11+ and Pydantic 2:

```bash
./scripts/validate.sh
```

Generate or refresh the sample bundle:

```bash
PYTHONPATH=packages/tracecase-model/src:packages/tracecase-bundle/src \
  python scripts/generate_sample_bundle.py
```

Inspect it through the CLI:

```bash
PYTHONPATH=packages/tracecase-model/src:packages/tracecase-bundle/src:packages/tracecase-cli/src \
  python -m tracecase_cli inspect fixtures/bundles/minimal-success.tracecase
```

## Optional Django API

Install the API dependencies declared in `apps/api/requirements.txt`, then:

```bash
cd apps/api
python manage.py runserver
```

The API discovers bundles beneath `TRACECASE_BUNDLE_ROOT`, defaulting to `fixtures/bundles`.

## Optional React Workbench

```bash
cd apps/workbench
npm install
npm run dev
```

Set `VITE_TRACECASE_API_BASE` if the API is not served from `http://localhost:8000/api`.

## Architectural constraints

1. Core semantic packages never import Django, Celery, OpenTelemetry, React, or Pathforge.
2. Technology-specific data enters through future adapters and namespaced extensions.
3. Evidence, normalized semantics, and derived interpretation remain separate layers.
4. Frozen bundle payloads are immutable by contract and independently checksum-verifiable.
5. Unknown namespaced extensions are preserved but cannot redefine core fields.
