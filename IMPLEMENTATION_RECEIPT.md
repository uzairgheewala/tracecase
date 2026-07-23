# Milestone D implementation receipt

## Delivery contract

This milestone is delivered as a repository-relative delta over the validated Milestone C repository. The archive contains only added or modified files in their original paths. `DELTA_MANIFEST.json` records additions, modifications, deletions, sizes, and SHA-256 hashes.

## Roadmap scope

Milestone D implements Phases 12–13:

1. Privacy classification, redaction, validation, and shareable export.
2. Concrete distributed reference laboratory with generic fault bindings and live Workbench controls.

## Added packages

### `tracecase-policy`

Provides:

- three export profiles;
- ordered, schema-aware policy rules;
- field inventory and sensitivity accounting;
- deterministic tokenization, digesting, masking, truncation, removal, summarization, and rejection;
- referential-integrity preservation;
- prohibited-pattern scanning;
- export-validation reports;
- privacy-aware portable bundle export.

The shareable exporter does not copy source derived artifacts. It sanitizes canonical evidence, rebuilds graph/timeline/invariants/findings, copies only allowlisted supplements, and writes policy and validation artifacts into the integrity-covered derivative bundle.

### `tracecase-lab`

Provides:

- generic `LabBinding` contracts;
- deterministic `LabRunRequest`, events, receipts, run results, and comparison results;
- an in-process reference workflow;
- fault-to-lifecycle bindings;
- automatic graph assembly, timeline generation, invariant evaluation, bounded analysis, and semantic comparison.

The reference binding is academic in presentation but generic in execution semantics. Downstream packages receive ordinary canonical cases and do not import lab-specific types.

## Distributed reference application

`apps/reference-lab` adds a Dockerized Django/Celery/PostgreSQL/Redis/mock-SIS workflow with:

- transcript-import API;
- import and enrollment persistence;
- transaction-safe healthy publication using `transaction.on_commit`;
- Celery normalization and retry behavior;
- mock external extraction service;
- shared JSONL evidence sink;
- controlled generic fault headers;
- dedicated non-production deployment configuration.

## Privacy behavior validated

The privacy-capture case contains deliberately injected credentials, student identifiers, free text, and transcript-like content.

Under `policy.shareable.v1` its inventory contains 1,029 traversed fields:

- 953 retained;
- 62 selected for tokenization;
- 11 selected for summarization;
- 3 selected for removal.

The deterministic transformation report records 63 actual transformations:

- 52 tokenizations;
- 8 summaries;
- 3 removals.

The resulting case has zero policy violations, passes prohibited-pattern validation, preserves canonical references, carries the `shareable` bundle profile, and verifies in both directory and ZIP form.

## Reference-lab behavior validated

The healthy workflow contains 10 source events, 10 canonical nodes, two durable effects, 12 satisfied invariants, one not-applicable invariant, and zero findings.

Generic fault bindings produce the expected bounded outcomes:

- context loss → required-continuity violation;
- duplicate effect → at-most-once violation and duplicate durable-effect finding;
- publish before commit → read-after-visibility violation;
- stale state → freshness violation;
- schema skew → compatibility violation;
- prohibited capture → privacy violation;
- broken link → observability-linkage violation while preserving the underlying effects.

The context comparison aligns all 10 operations without ambiguity and selects the worker normalization boundary at 205 ms as the first consequential divergence, where `tenant_id` changes from the institution token to absent.

## Workbench additions

### Redact & Export

- case and policy selection;
- field classification inventory;
- action and sensitivity summaries;
- deterministic transformation preview;
- unresolved violation display;
- shareable export request;
- export-path and validation results.

### Live Lab

- concrete binding and fault selection;
- seed and tenant/principal controls;
- baseline, candidate, and comparison execution;
- persistence to portable bundles;
- graph, timeline, semantics, invariant, and finding views;
- first-divergence presentation.

## API additions

- `GET /api/privacy-policies`
- `POST /api/cases/{case_id}/privacy-inventory`
- `POST /api/cases/{case_id}/redaction-preview`
- `POST /api/cases/{case_id}/shareable-export`
- `GET /api/lab-bindings`
- `POST /api/lab-runs`
- `POST /api/lab-comparisons`
- `POST /api/lab-runs/persist`

## CLI additions

- `policy-list`
- `privacy-inventory`
- `redaction-preview`
- `export-shareable`
- `lab-bindings`
- `lab-run`
- `lab-compare`

## Portable Milestone D fixtures

- `reference-lab-baseline.tracecase`
- `reference-lab-context-loss.tracecase`
- `reference-lab-duplicate-effect.tracecase`
- `reference-lab-publish-before-commit.tracecase`
- `reference-lab-privacy-capture.tracecase`
- `reference-lab-observability-gap.tracecase`
- `reference-lab-context-comparison.tracecase`
- `reference-lab-shareable.tracecase`

Each has an equivalent ZIP transport archive. Lab bundles contain source events, run receipts, graph/timeline artifacts, invariant reports, analyzer findings, and derived semantic projections. The comparison bundle additionally contains alignments and divergences. The shareable bundle contains redaction policy, report, export validation, and recomputed sanitized analysis.

## Validation result

The final working repository passed:

```text
Architecture dependency checks passed.
46 tests passed.
18 directory-form bundles verified.
8 Milestone D ZIP bundles opened and verified.
Invariant, analyzer, and semantic comparison CLI smoke tests passed.
Policy inventory, redaction preview, and shareable export CLI smoke tests passed.
Reference-lab binding, execution, and comparison CLI smoke tests passed.
Temporary shareable directory and ZIP exports verified.
Python compilation passed.
Workbench TypeScript/TSX syntax transpilation passed for 4 source files.
```

The complete local Vite production build was not run because the npm dependency tree is unavailable in the execution container. CI performs `npm install` and `npm run build` in a network-enabled environment.

The distributed Docker Compose topology was not launched in this container because Docker is unavailable. Its Python source compiled successfully; the deterministic in-process realization, API contracts, generated evidence, invariant outcomes, analysis, comparison, and portable bundles were fully exercised.

## Architectural guarantees

- Source and shareable bundles are separate immutable cases.
- Redaction preserves canonical references.
- Unknown supplements are omitted unless explicitly allowlisted safe.
- Derived artifacts are recomputed from disclosed evidence.
- Policy, transformation, omission, validation, and integrity results remain auditable.
- Generic fault identities are independent of Django and Celery implementation details.
- The reference lab uses ordinary canonical cases, invariant results, findings, and comparisons.
- Observability faults do not alter the modeled ground-truth effects.
- Fault injection remains isolated from production deployment paths.

## Deferred to later milestones

- Coverage observatory and automatic counterexample minimization.
- Large-case streaming, migrations, and compatibility hardening.
- Full OSS packaging and extension-author onboarding.
- Pathforge-specific instrumentation and semantic extensions.
