# Milestone E architecture

Milestone E completes the initial Tracecase roadmap by adding four systems above the immutable bundle, execution graph, invariant, analyzer, comparison, privacy, and laboratory layers.

## Coverage plane

`tracecase-coverage` evaluates supplied scenario instances against the valid points implied by the versioned scenario registry. Coverage is not a flat count of examples. It is a ledger across:

- scenario families;
- semantic-universe axes;
- topology motifs;
- fault operators;
- invariants;
- observability profiles;
- valid family/fault/profile interactions;
- observed invariant outcomes;
- synthetic versus concrete realizations.

The ledger distinguishes covered, uncovered, invalid, and unsupported points. Recommendations rank scenario families by how many presently uncovered valid points one additional execution could witness.

The minimizer remains generic by accepting a preservation oracle. It performs deterministic delta-debugging over declarative scenario inputs without importing a particular invariant or analyzer implementation.

## Compatibility and hardening plane

`tracecase-compat` treats compatibility, migration, recoverability, and large-case queryability as explicit contracts.

- Bundle-format assessment declares compatible, migratable, incompatible, or unknown status.
- Migration plans are versioned and loss characteristics are explicit.
- Health scans combine content-integrity verification with JSONL readability and recovery advice.
- Query indexes provide component, operation, identity, effect, and bounded-neighborhood lookups.
- Bundle archive extraction enforces entry-count, member-size, aggregate-size, path, and compression-ratio limits.
- `BundleReader.read_jsonl_page` allows bounded progressive access to large evidence streams.

Unknown namespaced extensions remain preserved rather than silently discarded.

## OSS and extension plane

`tracecase-sdk` exposes a small framework-independent event surface:

- context binding through `contextvars`;
- operation start/end and error events;
- domain events;
- logical effects;
- in-memory and JSONL sinks;
- adapter and analyzer plugin protocols;
- duplicate-safe plugin registration.

The SDK depends only on the canonical model. Django, Celery, OpenTelemetry, Pathforge, and the Workbench remain edge integrations.

## Pathforge integration plane

`tracecase-pathforge` is an isolated integration package. It maps Pathforge academic-domain events and workflow metadata into canonical Tracecase operations while retaining all domain-specific fields under `pathforge.academic`.

The generic core does not import Pathforge. The integration package may consume public model, graph, invariant, analyzer, comparison, and SDK contracts.

The initial requirement-audit binding emits:

- audit requested;
- candidate generation;
- solver completion;
- explanation generation;
- durable audit persistence.

Generic context-continuity, effect-eventuality, schema-compatibility, identity, observability, and semantic-comparison systems operate without Pathforge-specific branches.

## Dependency direction

```text
Pathforge / API / Workbench / external applications
                       ↓
            tracecase-pathforge
                       ↓
              tracecase-sdk
                       ↓
model ← graph ← invariants ← analyzers ← compare
  ↑          coverage       compatibility
  └────────── bundle ─────────────────────┘
```

No core package imports `tracecase_pathforge`. Coverage does not depend on the reference lab or application bindings. Compatibility does not interpret business-domain semantics.
