# Milestone C implementation receipt

## Delivery contract

This milestone is delivered as a repository-relative delta over the validated Milestone B repository. The archive contains only added or modified files in their original paths. `DELTA_MANIFEST.json` records additions, modifications, deletions, sizes, and SHA-256 hashes.

## Roadmap scope

Milestone C implements Phases 9–11:

1. Generic invariant engine.
2. Bounded evidence-linked analyzer family pack.
3. Semantic execution comparison and synchronized comparison UI.

## Added packages

### `tracecase-invariants`

Provides versioned invariant contracts, evidence requirements, scope selectors, evaluator kinds, a deterministic runtime, minimal counterexamples, evaluation traces, and six-state outcomes.

The default registry contains 13 framework-neutral invariants spanning continuity, isolation, liveness, ordering, consistency, compatibility, resources, observability, and privacy.

### `tracecase-analyzers`

Provides analyzer definitions, run receipts, bounded findings, severity/category taxonomies, and a deterministic analyzer engine. Seven initial analyzer packs cover context, identity, retry/effects, transaction ordering, observability, resource amplification, and contract/privacy behavior.

### `tracecase-compare`

Provides topology-aware semantic signatures, constrained node alignment, ambiguity handling, divergence classification, noise suppression, temporal ranking, and first-meaningful-divergence selection.

## Existing package changes

- `tracecase-bundle` writes producer version `0.3.0`, points completed manifests to deterministic analysis/comparison artifacts, and fixes archive opening through temporary directories.
- `tracecase-scenarios` enriches generated execution metadata with family, topology, invariant, expected-effect, and expected-edge contracts.
- `tracecase-cli` adds `invariants`, `analyze`, and `compare` commands.
- API case services compute or load invariant and analysis reports and expose new endpoints.
- A new comparison API performs baseline/candidate semantic comparison.
- The Workbench adds invariant, finding, and comparison surfaces.

## Invariant behavior validated

The analyzed baseline fixture produces:

- 13 evaluated invariants;
- 9 satisfied;
- 4 not applicable;
- 0 violations;
- 0 findings.

The context-failure fixture produces one required-continuity violation and one high-severity bounded finding with a counterexample.

The duplicate-effect fixture produces one at-most-once violation and two high-severity findings: the generic invariant finding and the retry-specific duplicate durable-effect finding.

The causal-gap fixture preserves the underlying semantic workflow while producing one observability-linkage violation and two evidence-focused findings.

## Semantic comparison behavior validated

The context baseline/failure comparison produces:

- 4 aligned nodes;
- 0 baseline-only nodes;
- 0 candidate-only nodes;
- 0 ambiguous alignments;
- 1 consequential divergence.

The selected first meaningful divergence occurs at the consumer operation at 200 ms and identifies the missing `tenant.tenant_id` context field. Regenerated execution identities do not create false divergences.

Retry comparison tests additionally validate candidate-only attempts and duplicate durable-effect divergence.

## Portable Milestone C fixtures

- `context-analysis-baseline.tracecase`
- `context-analysis-failure.tracecase`
- `duplicate-effect-analysis.tracecase`
- `causal-gap-analysis.tracecase`
- `semantic-context-comparison.tracecase`

Each has an equivalent ZIP transport archive. Analyzed bundles include invariant reports, findings, analyzer run receipts, graph/timeline artifacts, and their prior scenario evidence. The comparison bundle includes case references, alignments, divergences, summary, and complete semantic comparison.

## Workbench additions

### Explore Cases

- invariant-result list with status and confidence;
- evidence-linked finding list;
- finding-to-node navigation;
- finding inspector with evidence class, limitations, and recommended inspection points;
- bundle summary counts for findings and violated invariants.

### Compare Executions

- baseline and candidate case selection;
- semantic alignment list;
- matched, missing, and ambiguous alignment states;
- divergence navigator;
- first meaningful divergence callout;
- divergence evidence and limitation inspector.

## API additions

- `GET /api/cases/{case_id}/invariants`
- `GET /api/cases/{case_id}/analysis`
- `POST /api/comparisons`

The comparison request requires `baseline_case_id` and `candidate_case_id`.

## Validation result

The final working repository passed:

```text
Architecture dependency checks passed.
37 tests passed.
10 directory-form bundles verified.
5 Milestone C ZIP bundles opened and verified.
Invariant CLI smoke test passed.
Analyzer CLI smoke test passed.
Semantic comparison CLI smoke test passed.
Python compilation passed.
Workbench TypeScript/TSX syntax transpilation passed for 4 source files.
```

A full local Vite production build was not run because npm dependency installation timed out in the execution container. The source syntax passed through the TypeScript compiler API, and CI performs `npm install` plus the complete `npm run build` in a network-enabled environment.

## Architectural guarantees

- Evidence, graph, invariant, finding, and comparison layers remain distinct.
- Missing evidence can yield `inconclusive` instead of fabricated certainty.
- Every finding cites evidence and exposes limitations.
- Comparison does not rely on run-local trace or span IDs.
- Generic packages do not import Django, Celery, OpenTelemetry, Pathforge, or application-specific code.
- Comparison does not depend on a particular analyzer pack.
- All derived artifacts are additive and integrity-covered.

## Deferred to Milestone D and later

- Privacy classification, redaction, and export policy engine.
- Real distributed reference laboratory and live fault injection.
- Coverage observatory and scenario minimization.
- Large-case hardening and schema migration systems.
- Pathforge-specific extensions and analyzers.
