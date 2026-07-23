# Milestone B implementation receipt

## Delivery form

This milestone is delivered as a **delta over Milestone A**. The ZIP contains only new or modified repository files in their original repo-relative paths. Applying it consists of extracting the archive over the Milestone A repository root.

No Milestone A source file is removed by this delta.

## Implemented scope

Milestone B implements Phases 4–8 of the roadmap.

### Phase 4 — Scenario universe and registry

- Added the `tracecase-scenarios` package.
- Defined versioned semantic universes spanning topology, propagation, state/effects, time/concurrency, failure/recovery, contract evolution, resources/performance, isolation/privacy, deployment/configuration and observability/evidence.
- Added typed topology motifs, roles, edges, context contracts, effect templates and resource templates.
- Added parameter domains, admissibility constraints, expected-invariant records, minimization hints and coverage dimensions.
- Added 14 initial generic scenario families and 17 reusable fault operators.
- Exported portable JSON registry snapshots under `registries/`.
- Kept all families framework- and domain-neutral.

### Phase 5 — Scenario composition and generation

- Added `ScenarioDefinition`, `ScenarioInstance`, `FaultApplication` and observability-profile contracts.
- Implemented deterministic instance resolution from a definition and seed.
- Added typed parameter coercion and domain validation.
- Added admissibility validation with stable diagnostics.
- Added deterministic instance digests and coverage points.
- Added exact, sampled, constrained exhaustive and pairwise covering-set generation.
- Added CLI scenario listing and deterministic generation commands.
- Added a reusable repository delta builder for all subsequent milestone deliveries.
- Added Django scenario-family and scenario-generation endpoints.
- Added a functional scenario-construction surface to the React Workbench.

### Phase 6 — Synthetic execution and evidence engine

- Implemented a framework-neutral synthetic execution engine.
- Materialized topology roles into canonical components, boundaries, nodes, observations, contexts, state facts and effects.
- Separated semantic fault application from observability degradation.
- Preserved both ground-truth and observed cases in reproducible synthetic bundles.
- Added exact synthetic oracle outcomes and coverage metadata.
- Implemented semantic operators for context loss/mutation, duplicate/omitted effects, timing/order changes, schema skew, capacity exhaustion and execution amplification.
- Implemented observability operators for broken trace linkage, dropped evidence, clock skew, contradictory observations and prohibited sensitive capture.

### Phase 7 — Collection and adapter framework

- Added the `tracecase-collectors` package.
- Defined source-adapter discovery, collection and normalization contracts.
- Added raw-record, candidate-record, fragment, request, result and diagnostic models.
- Added a collection coordinator with partial-failure isolation.
- Added strict tenant-scope validation before fragment merge.
- Added an in-memory canonical-fragment adapter.
- Added an OpenTelemetry JSON adapter supporting resource/scope span and simplified span representations.
- Added a structured-event adapter for request, task, SQL, HTTP and domain-event style inputs.
- Preserved source-native IDs, raw-record digests and provenance through normalization.

### Phase 8 — Execution-graph assembly and timeline

- Added the `tracecase-graph` package.
- Implemented deterministic graph assembly over frozen canonical evidence.
- Preserved all source nodes and relations unchanged.
- Added derived parent-span, workflow, logical-operation, task/retry, message and repeated-effect relations.
- Added identity groups across trace, workflow, run, logical-operation, task, message, idempotency and tenant dimensions.
- Added context-flow reconstruction and continuity status.
- Added logical-effect groups and durable-effect counts.
- Added partial temporal constraints and contradiction-preserving graph warnings.
- Added connected-component and disconnected-fragment reporting.
- Added component-lane timeline projection.
- Added CLI graph summaries and Django graph/timeline endpoints.
- Upgraded the Workbench with an interactive SVG graph, multi-lane timeline, semantic identity/context/effect views and node-level evidence inspection.

## Bundle changes

The bundle implementation remains independent of scenario, collector and graph packages.

Milestone B adds:

- scenario and collection descriptors in the manifest;
- generic `SupplementalArtifact` support;
- synthetic, collection, registry, analysis and model supplement roots;
- optional artifact lookup and JSON loading;
- graph, timeline, scenario, oracle and ground-truth artifacts in synthetic benchmark bundles;
- evidence-digest coverage for synthetic and collection evidence layers.

Every supplemental artifact remains content-indexed and checksum-covered.

## Generated fixtures

The validation process generates and verifies:

1. `minimal-success.tracecase` — Milestone A regression fixture.
2. `context-continuity-baseline.tracecase` — intact required context.
3. `context-continuity-failure.tracecase` — semantic context disappearance.
4. `duplicate-effect-failure.tracecase` — retry lineage with two durable logical effects.
5. `causal-gap-observed.tracecase` — intact ground truth with deliberately broken observed linkage.

Each fixture is available as both a directory-form bundle and ZIP transport archive.

## Tests added

- Scenario registry and deterministic-generation tests.
- Pairwise covering-set tests.
- Semantic-fault versus observability-fault separation tests.
- Synthetic oracle and case-generation tests.
- OpenTelemetry and structured-event normalization tests.
- Partial adapter failure and tenant-scope rejection tests.
- Identity, retry, message, effect-group, context-flow and timeline graph tests.
- Supplemental bundle round-trip and integrity tests.
- All Milestone A conformance and tamper-detection tests remain active.

## Validation performed

The final backend validation run completed successfully:

```text
Architecture dependency checks passed.
22 tests passed.
5 directory bundles verified.
Missing paths: 0.
Digest mismatches: 0.
Unexpected paths: 0.
Scenario CLI smoke tests passed.
Graph CLI smoke tests passed.
Python compilation passed.
TypeScript/TSX syntax transpilation passed.
```

The four Milestone B graph fixtures also reconstruct successfully with expected identity, context, retry/effect and temporal projections.

## UI validation boundary

The Workbench source was syntax-transpiled with TypeScript 5.8.3. A complete React/Vite dependency installation could not be completed in the execution container because npm package retrieval timed out. The repository CI workflow installs the pinned dependencies and runs the full TypeScript and Vite production build in an environment with package access.

## Intentionally deferred to Milestone C

- Declarative invariant evaluation runtime.
- Satisfied, violated, inconclusive and contradicted invariant results.
- Bounded analyzer families and forensic findings.
- Minimal counterexample extraction.
- Semantic baseline/candidate alignment.
- First meaningful divergence analysis.
- Full privacy transformation and shareable-export policy engine.

## Architectural guarantees introduced

1. Scenario families are generic semantic mechanisms, not named application incidents.
2. Scenario instances are deterministic and content-addressable.
3. Semantic faults alter ground truth; observability faults alter only evidence.
4. Adapters cannot silently merge evidence across tenant scope.
5. Graph assembly is additive and does not rewrite source evidence.
6. Every relationship remains classified by derivation type.
7. Scenario and graph artifacts do not reverse bundle-package dependencies.
8. All generated fixtures remain portable and independently verifiable.
