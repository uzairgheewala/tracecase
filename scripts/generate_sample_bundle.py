from __future__ import annotations

import hashlib
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

from tracecase_bundle import BundleBuilder
from tracecase_model import (
    Boundary,
    BoundaryKind,
    CaseCategory,
    CaseEvidence,
    CaseSpecification,
    Component,
    ComponentKind,
    ContextField,
    DerivationKind,
    Effect,
    EffectKind,
    EvidenceClassification,
    ExecutionCase,
    ExecutionIdentitySet,
    ExecutionModel,
    ExecutionNode,
    ExecutionRelation,
    NodeKind,
    Observation,
    ObservationKind,
    PropagationContract,
    ProvenanceRef,
    RelationKind,
    Resource,
    SensitivityLabel,
    SourceDescriptor,
    StateFact,
    SystemModel,
    TimeObservation,
)
from tracecase_model.execution import EffectDurability

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "fixtures" / "bundles" / "minimal-success.tracecase"
ARCHIVE = ROOT / "fixtures" / "bundles" / "minimal-success.tracecase.zip"


def sha(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode()).hexdigest()


def time_at(base: datetime, milliseconds: int, clock: str) -> TimeObservation:
    return TimeObservation(
        raw_timestamp=base + timedelta(milliseconds=milliseconds),
        normalized_timestamp=base + timedelta(milliseconds=milliseconds),
        clock_ref=clock,
        precision_ns=1_000_000,
        normalization_method="fixture_identity",
    )


def build_case() -> ExecutionCase:
    base = datetime(2026, 7, 23, 9, 0, tzinfo=timezone.utc)
    sources = (
        SourceDescriptor(
            source_id="source.otel",
            source_kind="otel_export",
            name="reference-lab",
            captured_at=base + timedelta(seconds=1),
        ),
    )
    components = (
        Component(component_id="component.frontend", name="Workbench client", kind=ComponentKind.FRONTEND),
        Component(component_id="component.api", name="Tracecase API", kind=ComponentKind.API),
        Component(component_id="component.worker", name="Import worker", kind=ComponentKind.WORKER),
        Component(component_id="component.database", name="PostgreSQL", kind=ComponentKind.DATABASE),
    )
    boundaries = (
        Boundary(
            boundary_id="boundary.http",
            kind=BoundaryKind.HTTP,
            source_component_ref="component.frontend",
            target_component_ref="component.api",
            name="POST /imports",
        ),
        Boundary(
            boundary_id="boundary.task",
            kind=BoundaryKind.MESSAGE_PUBLISH,
            source_component_ref="component.api",
            target_component_ref="component.worker",
            name="normalize-import",
        ),
        Boundary(
            boundary_id="boundary.database",
            kind=BoundaryKind.DATABASE,
            source_component_ref="component.worker",
            target_component_ref="component.database",
            name="enrollment projection",
        ),
    )
    resources = (
        Resource(
            resource_id="resource.import-run",
            kind="database_row",
            name="ImportRun:1842",
            owner_component_ref="component.database",
            sensitivity={SensitivityLabel.TENANT_IDENTIFIER},
        ),
    )
    system = SystemModel(
        system_id="system.reference-lab",
        name="Tracecase reference laboratory",
        components=components,
        boundaries=boundaries,
        resources=resources,
    )

    observations = tuple(
        Observation(
            observation_id=f"observation.{name}",
            kind=kind,
            provenance=ProvenanceRef(source_id="source.otel", source_native_id=name, payload_digest=sha(name)),
            captured_at=base + timedelta(seconds=1),
            event_time=time_at(base, offset, clock),
            sensitivity={SensitivityLabel.INTERNAL},
        )
        for name, kind, offset, clock in (
            ("ui", ObservationKind.FRONTEND_EVENT, 0, "clock.browser"),
            ("request", ObservationKind.SPAN, 10, "clock.api"),
            ("transaction", ObservationKind.SPAN, 20, "clock.api"),
            ("publish", ObservationKind.TASK_EVENT, 40, "clock.api"),
            ("task", ObservationKind.TASK_EVENT, 80, "clock.worker"),
            ("write", ObservationKind.SQL_EVENT, 100, "clock.database"),
        )
    )

    contexts = (
        ContextField(
            context_id="context.tenant.request",
            namespace="tenant",
            field_name="institution_id",
            value="institution-17",
            propagation_contract=PropagationContract.REQUIRED,
            origin_node_ref="node.request",
            observed_at_node_ref="node.request",
            sensitivity={SensitivityLabel.TENANT_IDENTIFIER},
        ),
        ContextField(
            context_id="context.tenant.task",
            namespace="tenant",
            field_name="institution_id",
            value="institution-17",
            propagation_contract=PropagationContract.REQUIRED,
            origin_node_ref="node.request",
            observed_at_node_ref="node.task",
            sensitivity={SensitivityLabel.TENANT_IDENTIFIER},
        ),
    )

    identities = ExecutionIdentitySet(
        trace_id="4f000000000000000000000000000001",
        workflow_id="workflow-import-1842",
        tenant_id="institution-17",
        principal_id="user-redacted",
    )
    nodes = (
        ExecutionNode(
            node_id="node.ui",
            kind=NodeKind.USER_ACTION,
            operation="transcript_import.submit",
            component_ref="component.frontend",
            boundary_refs=("boundary.http",),
            identities=identities,
            timing=time_at(base, 0, "clock.browser"),
            end_time=time_at(base, 5, "clock.browser"),
            status="ok",
            observation_refs=("observation.ui",),
        ),
        ExecutionNode(
            node_id="node.request",
            kind=NodeKind.REQUEST_HANDLER,
            operation="POST /imports",
            component_ref="component.api",
            boundary_refs=("boundary.http", "boundary.task"),
            identities=identities.model_copy(update={"span_id": "span-request", "request_id": "request-1842"}),
            context_refs=("context.tenant.request",),
            timing=time_at(base, 10, "clock.api"),
            end_time=time_at(base, 60, "clock.api"),
            status="ok",
            observation_refs=("observation.request",),
        ),
        ExecutionNode(
            node_id="node.transaction",
            kind=NodeKind.TRANSACTION,
            operation="create import run",
            component_ref="component.database",
            boundary_refs=("boundary.database",),
            identities=identities.model_copy(update={"span_id": "span-tx", "transaction_id": "tx-1842"}),
            timing=time_at(base, 20, "clock.api"),
            end_time=time_at(base, 50, "clock.api"),
            status="committed",
            observation_refs=("observation.transaction",),
        ),
        ExecutionNode(
            node_id="node.publish",
            kind=NodeKind.MESSAGE_PUBLISH,
            operation="normalize-import.publish",
            component_ref="component.api",
            boundary_refs=("boundary.task",),
            identities=identities.model_copy(update={"span_id": "span-publish", "message_id": "message-1842"}),
            timing=time_at(base, 40, "clock.api"),
            end_time=time_at(base, 42, "clock.api"),
            status="ok",
            observation_refs=("observation.publish",),
        ),
        ExecutionNode(
            node_id="node.task",
            kind=NodeKind.TASK_ATTEMPT,
            operation="normalize-import",
            component_ref="component.worker",
            boundary_refs=("boundary.task", "boundary.database"),
            identities=identities.model_copy(update={
                "span_id": "span-task",
                "task_id": "task-1842",
                "task_attempt": 1,
                "message_id": "message-1842",
                "operation_attempt_id": "attempt-1",
            }),
            context_refs=("context.tenant.task",),
            timing=time_at(base, 80, "clock.worker"),
            end_time=time_at(base, 150, "clock.worker"),
            status="ok",
            effect_refs=("effect.import-updated",),
            observation_refs=("observation.task",),
        ),
        ExecutionNode(
            node_id="node.write",
            kind=NodeKind.WRITE,
            operation="import_run.update",
            component_ref="component.database",
            boundary_refs=("boundary.database",),
            identities=identities.model_copy(update={"span_id": "span-write", "transaction_id": "tx-worker-1842"}),
            timing=time_at(base, 100, "clock.database"),
            end_time=time_at(base, 120, "clock.database"),
            status="ok",
            state_refs=("fact.import-status",),
            effect_refs=("effect.import-updated",),
            observation_refs=("observation.write",),
        ),
    )

    state_facts = (
        StateFact(
            fact_id="fact.import-status",
            subject_ref="resource.import-run",
            property_name="status",
            value="completed",
            observed_time=time_at(base, 120, "clock.database"),
            observation_ref="observation.write",
            transaction_ref="node.write",
        ),
    )
    effects = (
        Effect(
            effect_id="effect.import-updated",
            kind=EffectKind.STATE_UPDATE,
            logical_effect_key="import-run/1842/completed",
            producer_node_ref="node.task",
            target_resource_ref="resource.import-run",
            operation="set completed",
            transaction_ref="node.write",
            idempotency_key="import-1842-completion",
            durability=EffectDurability.DURABLE,
            completion_status="completed",
            evidence_refs=("observation.write",),
        ),
    )
    relations = (
        ExecutionRelation(
            relation_id="relation.ui-request",
            kind=RelationKind.INVOKES,
            source_ref="node.ui",
            target_ref="node.request",
            derivation=DerivationKind.EXPLICIT,
            evidence_refs=("observation.ui", "observation.request"),
        ),
        ExecutionRelation(
            relation_id="relation.request-transaction",
            kind=RelationKind.CONTAINS,
            source_ref="node.request",
            target_ref="node.transaction",
            derivation=DerivationKind.SOURCE_NATIVE,
            evidence_refs=("observation.request", "observation.transaction"),
        ),
        ExecutionRelation(
            relation_id="relation.request-publish",
            kind=RelationKind.PUBLISHES,
            source_ref="node.request",
            target_ref="node.publish",
            derivation=DerivationKind.EXPLICIT,
            evidence_refs=("observation.publish",),
        ),
        ExecutionRelation(
            relation_id="relation.publish-task",
            kind=RelationKind.DELIVERS,
            source_ref="node.publish",
            target_ref="node.task",
            derivation=DerivationKind.SOURCE_NATIVE,
            evidence_refs=("observation.publish", "observation.task"),
        ),
        ExecutionRelation(
            relation_id="relation.task-write",
            kind=RelationKind.WRITES_TO,
            source_ref="node.task",
            target_ref="node.write",
            derivation=DerivationKind.EXPLICIT,
            evidence_refs=("observation.task", "observation.write"),
        ),
        ExecutionRelation(
            relation_id="relation.task-effect",
            kind=RelationKind.PRODUCES_EFFECT,
            source_ref="node.task",
            target_ref="effect.import-updated",
            derivation=DerivationKind.DETERMINISTIC,
            evidence_refs=("observation.write",),
        ),
    )
    execution = ExecutionModel(
        execution_id="execution.minimal-success",
        nodes=nodes,
        relations=relations,
        contexts=contexts,
        state_facts=state_facts,
        effects=effects,
        observations=observations,
        evidence_classification=EvidenceClassification.RECORDED,
    )
    return ExecutionCase(
        specification=CaseSpecification(
            case_id="case.minimal-success",
            title="Minimal successful transcript import",
            category=CaseCategory.OBSERVED_SINGLE,
            description="Milestone A fixture exercising HTTP, transaction, async task, context, state, and effect semantics.",
            created_at=base,
            roots=({"kind": "workflow_id", "value_token": "workflow-import-1842"},),
        ),
        system=system,
        evidence=CaseEvidence(sources=sources, execution=execution),
    )


def main() -> None:
    if OUTPUT.exists():
        shutil.rmtree(OUTPUT)
    if ARCHIVE.exists():
        ARCHIVE.unlink()
    builder = BundleBuilder(OUTPUT)
    result = builder.build(build_case())
    builder.pack(ARCHIVE)
    print(f"Generated {result.bundle_path}")
    print(f"Generated {ARCHIVE}")


if __name__ == "__main__":
    main()
