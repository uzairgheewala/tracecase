from __future__ import annotations

import hashlib
import random
from datetime import datetime, timedelta, timezone
from typing import Any

from tracecase_analyzers import AnalyzerEngine
from tracecase_compare import SemanticComparisonEngine
from tracecase_graph import GraphAssembler
from tracecase_model import (
    Boundary, BoundaryKind, CaseCategory, CaseEvidence, CaseSpecification, Component, ComponentKind,
    ContextField, DerivationKind, Effect, EffectKind, EvidenceClassification, ExecutionCase,
    ExecutionIdentitySet, ExecutionModel, ExecutionNode, ExecutionRelation, LifecycleStatus, NodeKind,
    Observation, ObservationKind, PropagationContract, ProvenanceRef, RelationKind, Resource,
    SensitivityLabel, SourceDescriptor, StateFact, SystemModel, TimeObservation,
)
from tracecase_model.case import CaseInterpretations
from tracecase_model.execution import EffectDurability

from .models import LabComparisonResult, LabEvent, LabMode, LabRunReceipt, LabRunRequest, LabRunResult, LabRunStatus
from .registry import get_binding


class ReferenceLab:
    def run(self, request: LabRunRequest) -> LabRunResult:
        binding = get_binding(request.binding_ref)
        if request.fault_operator_ref and request.fault_operator_ref not in binding.supported_faults:
            raise ValueError(f"fault is not supported by binding: {request.fault_operator_ref}")
        if request.mode is LabMode.DISTRIBUTED:
            raise RuntimeError("distributed mode is launched through apps/reference-lab/docker-compose.yml")
        start = datetime(2026, 7, 23, 18, 0, tzinfo=timezone.utc) + timedelta(seconds=request.seed)
        events = self._events(request, start)
        case = self._case(request, events, start)
        graph = GraphAssembler().assemble(case.evidence.execution)
        timeline = GraphAssembler().timeline(graph, case.system)
        analysis = AnalyzerEngine().analyze(case, graph)
        completed = start + timedelta(milliseconds=max((event.timestamp - start).total_seconds() * 1000 for event in events) + 50)
        receipt = LabRunReceipt(
            run_id=case.evidence.execution.execution_id,
            binding_ref=request.binding_ref,
            mode=request.mode,
            status=LabRunStatus.COMPLETED,
            started_at=start,
            completed_at=completed,
            fault_operator_ref=request.fault_operator_ref,
            observability_fault_ref=request.observability_fault_ref,
            event_count=len(events),
            case_id=case.specification.case_id,
            attributes={"family_ref": binding.family_ref, "seed": request.seed},
        )
        return LabRunResult(receipt=receipt, case=case, graph=graph, timeline=timeline, analysis=analysis, events=events)

    def compare(self, request: LabRunRequest) -> LabComparisonResult:
        baseline_request = request.model_copy(update={"fault_operator_ref": None, "observability_fault_ref": None, "include_sensitive_payload": False})
        baseline = self.run(baseline_request)
        candidate = self.run(request)
        comparison = SemanticComparisonEngine().compare(
            baseline.case, baseline.graph, candidate.case, candidate.graph,
        )
        return LabComparisonResult(baseline=baseline, candidate=candidate, comparison=comparison)

    def _events(self, request: LabRunRequest, start: datetime) -> tuple[LabEvent, ...]:
        rng = random.Random(request.seed)
        workflow = f"workflow-lab-{request.seed}"
        trace = hashlib.sha256(workflow.encode()).hexdigest()[:32]
        task = f"task-{request.seed}"
        message = f"message-{request.seed}"
        tenant = request.tenant_id
        if request.fault_operator_ref == "fault.context.drop.v1":
            worker_tenant: str | None = None
        else:
            worker_tenant = tenant
        base_identity: dict[str, Any] = {"trace_id": trace, "workflow_id": workflow, "run_id": f"run-{request.seed}", "tenant_id": tenant, "principal_id": request.principal_id}
        offsets = [0, 35, 55, 165, 205, 235, 270, 320, 370, 420]
        names = [
            ("browser", "transcript.upload", "user_action", None),
            ("django-api", "transcript_import.request", "request_handler", "browser.upload"),
            ("postgres", "import_run.transaction", "transaction", "api.request"),
            ("django-api", "transcript_import.publish", "message_publish", "db.transaction"),
            ("celery-worker", "transcript.normalize", "task_attempt", "api.publish"),
            ("postgres", "import_run.read", "read", "worker.normalize"),
            ("mock-sis", "transcript.extract", "external_request", "worker.lookup"),
            ("postgres", "enrollment_projection.write", "write", "external.extract"),
            ("audit-service", "degree_audit.recompute", "domain_operation", "projection.write"),
            ("notification-service", "import.completed.notify", "notification", "audit.recompute"),
        ]
        if request.fault_operator_ref == "fault.ordering.publish-before-commit.v1":
            offsets[2], offsets[3], offsets[4], offsets[5] = 160, 70, 110, 130
        events: list[LabEvent] = []
        event_ids = ["browser.upload", "api.request", "db.transaction", "api.publish", "worker.normalize", "worker.lookup", "external.extract", "projection.write", "audit.recompute", "notification.send"]
        for index, ((component, operation, node_kind, parent), event_id) in enumerate(zip(names, event_ids, strict=True)):
            identities = dict(base_identity)
            identities["span_id"] = f"span-{index+1}"
            if index:
                identities["parent_span_id"] = f"span-{index}"
            if index >= 3:
                identities.update({"task_id": task, "message_id": message})
            if index >= 4:
                identities["task_attempt"] = 1
                identities["tenant_id"] = worker_tenant
            attributes: dict[str, Any] = {"stage": index, "scenario_role_ref": event_id, "jitter_ms": rng.randint(0, 2)}
            sensitive: dict[str, Any] = {}
            if event_id == "api.request":
                attributes["course_count"] = len(request.transcript_courses)
                sensitive["student_email"] = "uzair.student@example.edu"
                sensitive["transcript_text"] = "DSC 100 A; DSC 180A A-; DSC 180B IP"
                if request.include_sensitive_payload or request.fault_operator_ref == "fault.privacy.capture-secret.v1":
                    sensitive["authorization"] = "Bearer very-secret-production-token"
                    attributes["authorization"] = sensitive["authorization"]
            if event_id == "api.publish":
                attributes["schema_version"] = "1.0"
            if event_id == "worker.normalize":
                attributes["schema_version"] = "2.0" if request.fault_operator_ref == "fault.contract.schema-skew.v1" else "1.0"
            if request.fault_operator_ref == "fault.consistency.stale-cache.v1" and event_id == "audit.recompute":
                attributes.update({"stale": True, "freshness_violation": True, "cache_version": 5, "required_version": 6})
            if request.observability_fault_ref == "fault.observability.break-link.v1" and event_id == "worker.normalize":
                identities["trace_id"] = hashlib.sha256(f"broken-{workflow}".encode()).hexdigest()[:32]
                identities.pop("parent_span_id", None)
            events.append(LabEvent(
                event_id=event_id, timestamp=start + timedelta(milliseconds=offsets[index]), component=component,
                operation=operation, node_kind=node_kind, status="ok", parent_event_id=parent,
                identities=identities, attributes=attributes, sensitive_attributes=sensitive,
            ))
        if request.fault_operator_ref in {"fault.effect.duplicate.v1", "fault.external.timeout-after-effect.v1"}:
            events.append(LabEvent(
                event_id="worker.retry", timestamp=start + timedelta(milliseconds=390), component="celery-worker",
                operation="transcript.normalize", node_kind="task_attempt", status="ok", parent_event_id="worker.normalize",
                identities={**base_identity, "span_id": "span-retry", "parent_span_id": "span-4", "task_id": task, "message_id": message, "task_attempt": 2, "tenant_id": worker_tenant, "idempotency_key": f"import-{request.seed}"},
                attributes={"stage": 4, "scenario_role_ref": "worker.retry", "retry_reason": "timeout_after_effect"},
            ))
        return tuple(events)

    def _case(self, request: LabRunRequest, events: tuple[LabEvent, ...], start: datetime) -> ExecutionCase:
        components = (
            Component(component_id="component.lab.browser", name="Browser", kind=ComponentKind.FRONTEND, role="browser", environment="lab"),
            Component(component_id="component.lab.api", name="Django API", kind=ComponentKind.API, role="api", environment="lab"),
            Component(component_id="component.lab.postgres", name="PostgreSQL", kind=ComponentKind.DATABASE, role="database", environment="lab"),
            Component(component_id="component.lab.worker", name="Celery Worker", kind=ComponentKind.WORKER, role="worker", environment="lab"),
            Component(component_id="component.lab.external", name="Mock SIS/OCR", kind=ComponentKind.EXTERNAL_SERVICE, role="external", environment="lab"),
            Component(component_id="component.lab.audit", name="Audit Service", kind=ComponentKind.SERVICE, role="audit", environment="lab"),
            Component(component_id="component.lab.notification", name="Notification Service", kind=ComponentKind.SERVICE, role="notification", environment="lab"),
        )
        comp_map = {"browser":"component.lab.browser", "django-api":"component.lab.api", "postgres":"component.lab.postgres", "celery-worker":"component.lab.worker", "mock-sis":"component.lab.external", "audit-service":"component.lab.audit", "notification-service":"component.lab.notification"}
        boundaries = (
            Boundary(boundary_id="boundary.lab.http", kind=BoundaryKind.HTTP, source_component_ref="component.lab.browser", target_component_ref="component.lab.api", name="Browser to API"),
            Boundary(boundary_id="boundary.lab.db", kind=BoundaryKind.DATABASE, source_component_ref="component.lab.api", target_component_ref="component.lab.postgres", name="API to PostgreSQL"),
            Boundary(boundary_id="boundary.lab.publish", kind=BoundaryKind.MESSAGE_PUBLISH, source_component_ref="component.lab.api", target_component_ref="component.lab.worker", name="Celery publish/consume"),
            Boundary(boundary_id="boundary.lab.external", kind=BoundaryKind.EXTERNAL_DEPENDENCY, source_component_ref="component.lab.worker", target_component_ref="component.lab.external", name="Worker to mock SIS"),
            Boundary(boundary_id="boundary.lab.audit", kind=BoundaryKind.FUNCTION_CALL, source_component_ref="component.lab.worker", target_component_ref="component.lab.audit", name="Projection to audit"),
            Boundary(boundary_id="boundary.lab.notify", kind=BoundaryKind.FUNCTION_CALL, source_component_ref="component.lab.audit", target_component_ref="component.lab.notification", name="Audit to notification"),
        )
        resources = (
            Resource(resource_id="resource.lab.import-run", kind="database_table", name="ImportRun", owner_component_ref="component.lab.postgres", sensitivity={SensitivityLabel.STUDENT_RECORD}),
            Resource(resource_id="resource.lab.enrollments", kind="database_table", name="Enrollments", owner_component_ref="component.lab.postgres", sensitivity={SensitivityLabel.STUDENT_RECORD}),
            Resource(resource_id="resource.lab.notification", kind="external_effect", name="Completion notification", owner_component_ref="component.lab.notification", sensitivity={SensitivityLabel.USER_IDENTIFIER}),
        )
        system = SystemModel(system_id="system.reference-lab", name="Tracecase distributed reference laboratory", components=components, boundaries=boundaries, resources=resources)
        source = SourceDescriptor(source_id="source.reference-lab", source_kind="lab_runtime", name="Tracecase reference laboratory", schema_ref="tracecase.lab-event.v1", captured_at=start + timedelta(seconds=1))
        nodes: list[ExecutionNode] = []
        observations: list[Observation] = []
        contexts: list[ContextField] = []
        relations: list[ExecutionRelation] = []
        node_by_event: dict[str, str] = {}
        observation_by_event: dict[str, str] = {}
        boundary_by_event = {"browser.upload":(), "api.request":("boundary.lab.http",), "db.transaction":("boundary.lab.db",), "api.publish":("boundary.lab.publish",), "worker.normalize":("boundary.lab.publish",), "worker.retry":("boundary.lab.publish",), "worker.lookup":("boundary.lab.db",), "external.extract":("boundary.lab.external",), "projection.write":("boundary.lab.db",), "audit.recompute":("boundary.lab.audit",), "notification.send":("boundary.lab.notify",)}
        for index, event in enumerate(events):
            node_id = f"node.lab.{event.event_id.replace('.', '-')}"
            obs_id = f"observation.lab.{event.event_id.replace('.', '-')}"
            node_by_event[event.event_id] = node_id
            observation_by_event[event.event_id] = obs_id
            sensitivity = {SensitivityLabel.INTERNAL}
            attrs = dict(event.attributes)
            if event.sensitive_attributes:
                attrs["captured_payload"] = event.sensitive_attributes
            observations.append(Observation(
                observation_id=obs_id, kind=self._observation_kind(event.node_kind),
                provenance=ProvenanceRef(source_id=source.source_id, source_native_id=event.event_id),
                captured_at=start + timedelta(seconds=1), event_time=self._time(event.timestamp, comp_map[event.component]),
                normalized_refs=(node_id,), attributes=attrs, sensitivity=sensitivity,
            ))
            node_kind = NodeKind(event.node_kind)
            identities = ExecutionIdentitySet(**event.identities)
            context_refs: list[str] = []
            if event.identities.get("tenant_id") is not None:
                context_id = f"context.lab.tenant.{event.event_id.replace('.', '-')}"
                contexts.append(ContextField(
                    context_id=context_id, namespace="tenant", field_name="tenant_id", value=event.identities["tenant_id"],
                    propagation_contract=PropagationContract.REQUIRED, origin_node_ref="node.lab.browser-upload",
                    observed_at_node_ref=node_id, sensitivity={SensitivityLabel.TENANT_IDENTIFIER},
                    extensions={"tracecase.scenario": {"contract_ref": "tenant-continuity", "required_role_refs": ["browser.upload", "api.request", "worker.normalize"]}},
                ))
                context_refs.append(context_id)
            end = event.timestamp + timedelta(milliseconds=20 if node_kind is not NodeKind.TRANSACTION else 100)
            nodes.append(ExecutionNode(
                node_id=node_id, kind=node_kind, operation=event.operation, component_ref=comp_map[event.component],
                boundary_refs=boundary_by_event[event.event_id], identities=identities, context_refs=tuple(context_refs),
                timing=self._time(event.timestamp, comp_map[event.component]), end_time=self._time(end, comp_map[event.component]),
                status=event.status, observation_refs=(obs_id,), sensitivity=sensitivity,
                attributes={**event.attributes, "scenario_role_ref": event.event_id},
            ))
        for event in events:
            if event.parent_event_id and event.parent_event_id in node_by_event:
                relations.append(ExecutionRelation(
                    relation_id=f"relation.lab.{event.parent_event_id.replace('.', '-')}.{event.event_id.replace('.', '-')}",
                    kind=self._relation_kind(event), source_ref=node_by_event[event.parent_event_id], target_ref=node_by_event[event.event_id],
                    derivation=DerivationKind.EXPLICIT, evidence_refs=(observation_by_event[event.parent_event_id], observation_by_event[event.event_id]),
                ))
        effects: list[Effect] = []
        projection_events = [event for event in events if event.event_id in {"projection.write", "worker.retry"}]
        for index, event in enumerate(projection_events):
            producer = node_by_event["projection.write"] if event.event_id == "projection.write" else node_by_event["worker.retry"]
            evidence = observation_by_event[event.event_id]
            effects.append(Effect(
                effect_id=f"effect.lab.enrollment.{index+1}", kind=EffectKind.STATE_UPDATE,
                logical_effect_key=f"enrollment-projection/import-{request.seed}", producer_node_ref=producer,
                target_resource_ref="resource.lab.enrollments", operation="upsert enrollments", idempotency_key=f"import-{request.seed}",
                durability=EffectDurability.DURABLE, completion_status="completed", evidence_refs=(evidence,),
                sensitivity={SensitivityLabel.STUDENT_RECORD}, attributes={"required": True, "maximum_durable_count": 1, "row_count": len(request.transcript_courses)},
            ))
        effects.append(Effect(
            effect_id="effect.lab.notification", kind=EffectKind.NOTIFICATION_SEND,
            logical_effect_key=f"notification/import-{request.seed}/completed", producer_node_ref=node_by_event["notification.send"],
            target_resource_ref="resource.lab.notification", operation="send completion notification", idempotency_key=f"notification-{request.seed}",
            durability=EffectDurability.DURABLE, completion_status="completed", evidence_refs=(observation_by_event["notification.send"],),
            sensitivity={SensitivityLabel.USER_IDENTIFIER}, attributes={"required": True, "maximum_durable_count": 1},
        ))
        facts = (
            StateFact(fact_id="fact.lab.import-status", subject_ref="resource.lab.import-run", property_name="status", value="completed", observed_time=self._time(start + timedelta(milliseconds=430), "component.lab.postgres"), observation_ref=observation_by_event["projection.write"], confidence={"score":1.0,"rationale":"lab state"}, sensitivity={SensitivityLabel.STUDENT_RECORD}),
        )
        node_updates: list[ExecutionNode] = []
        for node in nodes:
            refs = tuple(effect.effect_id for effect in effects if effect.producer_node_ref == node.node_id)
            state_refs = ("fact.lab.import-status",) if node.node_id == node_by_event["projection.write"] else ()
            node_updates.append(node.model_copy(update={"effect_refs": refs, "state_refs": state_refs}))
        execution = ExecutionModel(
            execution_id=f"execution.lab.{request.seed}.{'baseline' if not request.fault_operator_ref and not request.observability_fault_ref else 'candidate'}",
            nodes=tuple(node_updates), relations=tuple(relations), contexts=tuple(contexts), state_facts=facts, effects=tuple(effects), observations=tuple(observations), evidence_classification=EvidenceClassification.RECORDED,
            extensions={"tracecase.scenario": {"family_ref": "workflow.distributed-operation.v1", "expected_effects": [{"logical_effect_key": f"enrollment-projection/import-{request.seed}", "required": True}], "fault_operator_ref": request.fault_operator_ref, "observability_fault_ref": request.observability_fault_ref}},
        )
        case_id = f"case.lab.{request.seed}.{'baseline' if not request.fault_operator_ref and not request.observability_fault_ref else self._slug(request.fault_operator_ref or request.observability_fault_ref or 'candidate')}"
        return ExecutionCase(
            specification=CaseSpecification(case_id=case_id, title=f"Reference lab: {request.fault_operator_ref or request.observability_fault_ref or 'baseline'}", category=CaseCategory.HYBRID, description="Concrete transcript-import reference workflow bound to generic Tracecase fault semantics.", created_at=start, roots=({"kind":"workflow_id","value":f"workflow-lab-{request.seed}"},), privacy_policy_ref="policy.internal.v1", scenario_ref="lab.transcript-import.v1"),
            system=system, evidence=CaseEvidence(sources=(source,), execution=execution), interpretations=CaseInterpretations(), lifecycle=LifecycleStatus.COLLECTED,
            extensions={"tracecase.lab": {"binding_ref": request.binding_ref, "mode": request.mode.value}},
        )

    @staticmethod
    def _time(value: datetime, component: str) -> TimeObservation:
        return TimeObservation(raw_timestamp=value, normalized_timestamp=value, clock_ref=f"clock.{component.replace('component.', '')}", precision_ns=1_000_000, normalization_method="reference_lab_clock")

    @staticmethod
    def _observation_kind(node_kind: str) -> ObservationKind:
        return {"user_action":ObservationKind.FRONTEND_EVENT, "request_handler":ObservationKind.HTTP_EVENT, "transaction":ObservationKind.SQL_EVENT, "message_publish":ObservationKind.TASK_EVENT, "task_attempt":ObservationKind.TASK_EVENT, "external_request":ObservationKind.HTTP_EVENT, "write":ObservationKind.SQL_EVENT, "notification":ObservationKind.DOMAIN_EVENT}.get(node_kind, ObservationKind.DOMAIN_EVENT)

    @staticmethod
    def _relation_kind(event: LabEvent) -> RelationKind:
        if event.node_kind == "message_publish": return RelationKind.PUBLISHES
        if event.node_kind == "task_attempt": return RelationKind.CONSUMES if event.event_id == "worker.normalize" else RelationKind.RETRIES
        if event.node_kind == "write": return RelationKind.WRITES_TO
        return RelationKind.INVOKES

    @staticmethod
    def _slug(value: str) -> str:
        return "".join(char if char.isalnum() else "-" for char in value).strip("-")
