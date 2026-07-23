# Distributed reference laboratory

## Workflow

The initial binding represents:

```text
Browser upload
    → Django request
    → PostgreSQL import transaction
    → Celery publication
    → worker normalization
    → mock SIS/OCR request
    → enrollment projection
    → degree-audit recomputation
    → completion notification
```

It is an academic-planning example, but its canonical operations remain generic request, transaction, publication, task, read, external request, write, domain operation and notification nodes.

## Generic fault bindings

The binding supports:

- `fault.context.drop.v1`;
- `fault.ordering.publish-before-commit.v1`;
- `fault.effect.duplicate.v1`;
- `fault.consistency.stale-cache.v1`;
- `fault.contract.schema-skew.v1`;
- `fault.observability.break-link.v1`;
- `fault.privacy.capture-secret.v1`;
- `fault.external.timeout-after-effect.v1`.

Each fault is applied at a declared lifecycle point. It is not implemented as a hard-coded finding. Existing invariant and analyzer packages interpret the resulting canonical evidence.

## In-process mode

In-process mode is deterministic and requires no external services. It produces:

- `LabEvent` source events;
- a canonical `ExecutionCase`;
- an assembled execution graph;
- a partial-order timeline;
- invariant and analyzer results;
- a lab run receipt.

It is used by tests, generated fixtures and the Workbench Live Lab.

## Distributed mode

The compose deployment starts:

- PostgreSQL;
- Redis;
- Django API;
- Celery worker;
- mock SIS service;
- a shared JSONL evidence volume.

Run it from `apps/reference-lab`:

```bash
docker compose up --build
```

The API uses `transaction.on_commit` in the healthy path. The publish-before-commit operator deliberately bypasses that protection. Other faults are passed through the controlled lab request and task headers.

## Safety

The laboratory is not a production fault-injection service. It uses dedicated infrastructure, explicit supported fault references and non-production defaults. Fault controls must not be mounted into a normal application deployment.
