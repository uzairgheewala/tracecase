from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tracecase_model import (
    Boundary,
    BoundaryKind,
    Component,
    ComponentKind,
    DerivationKind,
    ExecutionIdentitySet,
    ExecutionNode,
    ExecutionRelation,
    NodeKind,
    Observation,
    ObservationKind,
    ProvenanceRef,
    RelationKind,
    SensitivityLabel,
    SourceDescriptor,
    TimeObservation,
)

from .models import (
    AdapterDiagnostic,
    CandidateRecord,
    CollectionFragment,
    CollectionRequest,
    DiagnosticSeverity,
    RawRecord,
)
from .utils import parse_timestamp, stable_id


class InMemoryFragmentAdapter:
    def __init__(self, fragment: CollectionFragment) -> None:
        self.adapter_id = fragment.adapter_id
        self.fragment = fragment

    def discover(self, request: CollectionRequest) -> tuple[CandidateRecord, ...]:
        return (
            CandidateRecord(
                candidate_id=stable_id("candidate.memory", request.request_id, self.fragment.fragment_id),
                adapter_id=self.adapter_id,
                source_native_id=self.fragment.fragment_id,
                summary="Pre-normalized in-memory fragment",
            ),
        )

    def collect(
        self,
        request: CollectionRequest,
        candidates: tuple[CandidateRecord, ...],
    ) -> tuple[RawRecord, ...]:
        return ()

    def normalize(
        self,
        request: CollectionRequest,
        records: tuple[RawRecord, ...],
    ) -> CollectionFragment:
        return self.fragment


class OtelJsonAdapter:
    adapter_id = "adapter.otel-json"

    def __init__(self, records: Iterable[Mapping[str, Any]], *, source_name: str = "OpenTelemetry JSON") -> None:
        self.source_name = source_name
        self.records = tuple(_flatten_otel_records(records))

    @classmethod
    def from_path(cls, path: Path) -> "OtelJsonAdapter":
        payload = json.loads(path.read_text(encoding="utf-8"))
        values = payload if isinstance(payload, list) else [payload]
        return cls(values, source_name=path.name)

    def discover(self, request: CollectionRequest) -> tuple[CandidateRecord, ...]:
        selectors = {(item.kind, item.value) for item in request.selectors}
        candidates: list[CandidateRecord] = []
        for record in self.records:
            trace_id = str(record.get("traceId") or record.get("trace_id") or "")
            span_id = str(record.get("spanId") or record.get("span_id") or "")
            attributes = _attributes(record)
            workflow_id = str(attributes.get("workflow.id") or attributes.get("workflow_id") or "")
            request_id = str(attributes.get("request.id") or attributes.get("request_id") or "")
            if selectors and not any(
                (kind == "trace_id" and value == trace_id)
                or (kind == "span_id" and value == span_id)
                or (kind == "workflow_id" and value == workflow_id)
                or (kind == "request_id" and value == request_id)
                for kind, value in selectors
            ):
                continue
            event_time = _otel_time(record.get("startTimeUnixNano") or record.get("start_time"))
            candidates.append(
                CandidateRecord(
                    candidate_id=stable_id("candidate.otel", trace_id, span_id),
                    adapter_id=self.adapter_id,
                    source_native_id=span_id or stable_id("span", record),
                    event_time=event_time,
                    summary=str(record.get("name") or "unnamed span"),
                    attributes={"trace_id": trace_id, "workflow_id": workflow_id},
                )
            )
        return tuple(candidates)

    def collect(
        self,
        request: CollectionRequest,
        candidates: tuple[CandidateRecord, ...],
    ) -> tuple[RawRecord, ...]:
        candidate_ids = {item.source_native_id for item in candidates}
        records: list[RawRecord] = []
        for record in self.records:
            span_id = str(record.get("spanId") or record.get("span_id") or "")
            if candidates and span_id not in candidate_ids:
                continue
            attrs = _attributes(record)
            records.append(
                RawRecord(
                    record_id=stable_id("record.otel", span_id, record.get("traceId")),
                    adapter_id=self.adapter_id,
                    source_native_id=span_id,
                    payload=dict(record),
                    event_time=_otel_time(record.get("startTimeUnixNano") or record.get("start_time")),
                    tenant_id=_optional_string(attrs.get("tenant.id") or attrs.get("tenant_id")),
                    schema_ref="opentelemetry.span.json",
                )
            )
        return tuple(records)

    def normalize(
        self,
        request: CollectionRequest,
        records: tuple[RawRecord, ...],
    ) -> CollectionFragment:
        captured_at = datetime.now(timezone.utc)
        source = SourceDescriptor(
            source_id="source.otel-json",
            source_kind="otel_json",
            name=self.source_name,
            schema_ref="opentelemetry.span.json",
            captured_at=captured_at,
        )
        components_by_service: dict[str, Component] = {}
        node_by_span: dict[str, ExecutionNode] = {}
        observations: list[Observation] = []
        diagnostics: list[AdapterDiagnostic] = []
        raw_by_span: dict[str, RawRecord] = {}

        for raw in records:
            record = _as_mapping(raw.payload)
            attrs = _attributes(record)
            resource_attrs = _as_mapping(record.get("resource_attributes", {}))
            service_name = str(
                resource_attrs.get("service.name")
                or attrs.get("service.name")
                or record.get("serviceName")
                or "unknown-service"
            )
            component_id = stable_id("component.otel", service_name)
            if service_name not in components_by_service:
                components_by_service[service_name] = Component(
                    component_id=component_id,
                    name=service_name,
                    kind=_component_kind(service_name, attrs),
                    role=_optional_string(attrs.get("service.role")),
                    version=_optional_string(resource_attrs.get("service.version")),
                    environment=_optional_string(resource_attrs.get("deployment.environment")),
                    attributes={"source_adapter": self.adapter_id},
                )
            span_id = str(record.get("spanId") or record.get("span_id") or raw.source_native_id)
            trace_id = str(record.get("traceId") or record.get("trace_id") or "")
            parent_span_id = _optional_string(record.get("parentSpanId") or record.get("parent_span_id"))
            start = raw.event_time or captured_at
            end = _otel_time(record.get("endTimeUnixNano") or record.get("end_time")) or start
            node_id = stable_id("node.otel", trace_id, span_id)
            observation_id = stable_id("observation.otel", trace_id, span_id)
            kind = _node_kind(record, attrs)
            identities = ExecutionIdentitySet(
                trace_id=trace_id or None,
                span_id=span_id or None,
                parent_span_id=parent_span_id,
                request_id=_optional_string(attrs.get("request.id") or attrs.get("request_id")),
                workflow_id=_optional_string(attrs.get("workflow.id") or attrs.get("workflow_id")),
                run_id=_optional_string(attrs.get("run.id") or attrs.get("run_id")),
                logical_operation_id=_optional_string(attrs.get("operation.id") or attrs.get("logical_operation_id")),
                task_id=_optional_string(attrs.get("messaging.message.id") or attrs.get("task.id") or attrs.get("task_id")),
                task_attempt=_optional_int(attrs.get("task.attempt") or attrs.get("task_attempt")),
                message_id=_optional_string(attrs.get("messaging.message.id") or attrs.get("message_id")),
                idempotency_key=_optional_string(attrs.get("idempotency.key") or attrs.get("idempotency_key")),
                transaction_id=_optional_string(attrs.get("db.transaction.id") or attrs.get("transaction_id")),
                tenant_id=_optional_string(attrs.get("tenant.id") or attrs.get("tenant_id")),
                principal_id=_optional_string(attrs.get("enduser.id") or attrs.get("principal_id")),
            )
            observation = Observation(
                observation_id=observation_id,
                kind=ObservationKind.SPAN,
                provenance=ProvenanceRef(
                    source_id=source.source_id,
                    source_native_id=span_id,
                ),
                captured_at=captured_at,
                event_time=TimeObservation(
                    raw_timestamp=start,
                    normalized_timestamp=start,
                    clock_ref=stable_id("clock.otel", service_name),
                    normalization_method="otel_source_timestamp",
                ),
                normalized_refs=(node_id,),
                attributes={
                    "span_kind": str(record.get("kind") or "unspecified"),
                    "status": record.get("status", {}),
                },
                sensitivity={SensitivityLabel.INTERNAL},
            )
            status = _status(record)
            node = ExecutionNode(
                node_id=node_id,
                kind=kind,
                operation=str(record.get("name") or "unnamed span"),
                component_ref=component_id,
                identities=identities,
                timing=observation.event_time,
                end_time=TimeObservation(
                    raw_timestamp=end,
                    normalized_timestamp=end,
                    clock_ref=stable_id("clock.otel", service_name),
                    normalization_method="otel_source_timestamp",
                ),
                status=status,
                observation_refs=(observation_id,),
                attributes={
                    "otel_span_kind": str(record.get("kind") or "unspecified"),
                    "otel_attributes": attrs,
                },
            )
            if not span_id:
                diagnostics.append(
                    AdapterDiagnostic(
                        diagnostic_id=stable_id("diagnostic.otel", raw.record_id, "missing-span-id"),
                        adapter_id=self.adapter_id,
                        severity=DiagnosticSeverity.WARNING,
                        code="missing_span_id",
                        message="Span did not contain a source-native span identifier.",
                        source_native_id=raw.source_native_id,
                    )
                )
            raw_by_span[span_id] = raw
            node_by_span[span_id] = node
            observations.append(observation)

        relations: list[ExecutionRelation] = []
        boundaries: dict[tuple[str, str], Boundary] = {}
        for span_id, node in node_by_span.items():
            parent_span_id = node.identities.parent_span_id
            if not parent_span_id or parent_span_id not in node_by_span:
                continue
            parent = node_by_span[parent_span_id]
            observation_refs = (*parent.observation_refs, *node.observation_refs)
            relations.append(
                ExecutionRelation(
                    relation_id=stable_id("relation.otel.parent", parent.node_id, node.node_id),
                    kind=RelationKind.PARENT_OF,
                    source_ref=parent.node_id,
                    target_ref=node.node_id,
                    derivation=DerivationKind.SOURCE_NATIVE,
                    evidence_refs=observation_refs,
                )
            )
            if parent.component_ref != node.component_ref:
                key = (parent.component_ref, node.component_ref)
                boundary = boundaries.get(key)
                if boundary is None:
                    boundary = Boundary(
                        boundary_id=stable_id("boundary.otel", *key),
                        kind=_boundary_kind(node.kind),
                        source_component_ref=parent.component_ref,
                        target_component_ref=node.component_ref,
                        name=f"{parent.operation} → {node.operation}",
                    )
                    boundaries[key] = boundary

        boundary_refs_by_component_pair = {
            (item.source_component_ref, item.target_component_ref): item.boundary_id
            for item in boundaries.values()
        }
        nodes = []
        for node in node_by_span.values():
            parent = node_by_span.get(node.identities.parent_span_id or "")
            boundary_refs = ()
            if parent and parent.component_ref != node.component_ref:
                boundary_refs = (
                    boundary_refs_by_component_pair[(parent.component_ref, node.component_ref)],
                )
            nodes.append(node.model_copy(update={"boundary_refs": boundary_refs}))

        return CollectionFragment(
            fragment_id=stable_id("fragment.otel", request.request_id, len(records)),
            adapter_id=self.adapter_id,
            sources=(source,),
            components=tuple(sorted(components_by_service.values(), key=lambda item: item.component_id)),
            boundaries=tuple(sorted(boundaries.values(), key=lambda item: item.boundary_id)),
            nodes=tuple(sorted(nodes, key=lambda item: item.node_id)),
            relations=tuple(sorted(relations, key=lambda item: item.relation_id)),
            observations=tuple(sorted(observations, key=lambda item: item.observation_id)),
            diagnostics=tuple(diagnostics),
        )


class StructuredEventAdapter:
    adapter_id = "adapter.structured-events"

    def __init__(self, records: Iterable[Mapping[str, Any]], *, source_name: str = "Structured events") -> None:
        self.records = tuple(dict(item) for item in records)
        self.source_name = source_name

    @classmethod
    def from_jsonl(cls, path: Path) -> "StructuredEventAdapter":
        records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        return cls(records, source_name=path.name)

    def discover(self, request: CollectionRequest) -> tuple[CandidateRecord, ...]:
        selectors = {(item.kind, item.value) for item in request.selectors}
        results: list[CandidateRecord] = []
        for index, record in enumerate(self.records):
            identities = _as_mapping(record.get("identities", {}))
            if selectors and not any(str(identities.get(kind, "")) == value for kind, value in selectors):
                continue
            source_native_id = str(record.get("event_id") or f"event-{index}")
            results.append(
                CandidateRecord(
                    candidate_id=stable_id("candidate.event", source_native_id),
                    adapter_id=self.adapter_id,
                    source_native_id=source_native_id,
                    event_time=parse_timestamp(record.get("timestamp", datetime.now(timezone.utc))),
                    summary=str(record.get("operation") or record.get("message") or "structured event"),
                )
            )
        return tuple(results)

    def collect(
        self,
        request: CollectionRequest,
        candidates: tuple[CandidateRecord, ...],
    ) -> tuple[RawRecord, ...]:
        selected = {item.source_native_id for item in candidates}
        results: list[RawRecord] = []
        for index, record in enumerate(self.records):
            source_native_id = str(record.get("event_id") or f"event-{index}")
            if candidates and source_native_id not in selected:
                continue
            identities = _as_mapping(record.get("identities", {}))
            results.append(
                RawRecord(
                    record_id=stable_id("record.event", source_native_id),
                    adapter_id=self.adapter_id,
                    source_native_id=source_native_id,
                    payload=record,
                    event_time=parse_timestamp(record.get("timestamp", datetime.now(timezone.utc))),
                    tenant_id=_optional_string(identities.get("tenant_id")),
                    schema_ref=_optional_string(record.get("schema_ref")) or "tracecase.structured-event.v1",
                )
            )
        return tuple(results)

    def normalize(
        self,
        request: CollectionRequest,
        records: tuple[RawRecord, ...],
    ) -> CollectionFragment:
        captured_at = datetime.now(timezone.utc)
        source = SourceDescriptor(
            source_id="source.structured-events",
            source_kind="structured_events",
            name=self.source_name,
            schema_ref="tracecase.structured-event.v1",
            captured_at=captured_at,
        )
        components: dict[str, Component] = {}
        nodes: list[ExecutionNode] = []
        observations: list[Observation] = []
        relations: list[ExecutionRelation] = []
        node_by_event_id: dict[str, str] = {}
        parent_by_event_id: dict[str, str] = {}
        for raw in records:
            record = _as_mapping(raw.payload)
            event_id = raw.source_native_id
            component_name = str(record.get("component") or "application")
            component_id = stable_id("component.event", component_name)
            components.setdefault(
                component_name,
                Component(
                    component_id=component_id,
                    name=component_name,
                    kind=ComponentKind(str(record.get("component_kind") or "service")),
                    role=_optional_string(record.get("component_role")),
                ),
            )
            node_id = stable_id("node.event", event_id)
            observation_id = stable_id("observation.event", event_id)
            identities = _as_mapping(record.get("identities", {}))
            timestamp = raw.event_time or captured_at
            observations.append(
                Observation(
                    observation_id=observation_id,
                    kind=ObservationKind(str(record.get("observation_kind") or "domain_event")),
                    provenance=ProvenanceRef(source_id=source.source_id, source_native_id=event_id),
                    captured_at=captured_at,
                    event_time=TimeObservation(
                        raw_timestamp=timestamp,
                        normalized_timestamp=timestamp,
                        clock_ref=stable_id("clock.event", component_name),
                        normalization_method="structured_event_timestamp",
                    ),
                    normalized_refs=(node_id,),
                    attributes=_json_mapping(record.get("attributes", {})),
                )
            )
            node_kind_value = str(record.get("node_kind") or "domain_operation")
            node = ExecutionNode(
                node_id=node_id,
                kind=NodeKind(node_kind_value),
                operation=str(record.get("operation") or record.get("message") or event_id),
                component_ref=component_id,
                identities=ExecutionIdentitySet(
                    trace_id=_optional_string(identities.get("trace_id")),
                    span_id=_optional_string(identities.get("span_id")),
                    parent_span_id=_optional_string(identities.get("parent_span_id")),
                    request_id=_optional_string(identities.get("request_id")),
                    workflow_id=_optional_string(identities.get("workflow_id")),
                    run_id=_optional_string(identities.get("run_id")),
                    logical_operation_id=_optional_string(identities.get("logical_operation_id")),
                    task_id=_optional_string(identities.get("task_id")),
                    task_attempt=_optional_int(identities.get("task_attempt")),
                    message_id=_optional_string(identities.get("message_id")),
                    idempotency_key=_optional_string(identities.get("idempotency_key")),
                    transaction_id=_optional_string(identities.get("transaction_id")),
                    tenant_id=_optional_string(identities.get("tenant_id")),
                    principal_id=_optional_string(identities.get("principal_id")),
                ),
                timing=observations[-1].event_time,
                status=str(record.get("status") or "unknown"),
                observation_refs=(observation_id,),
                attributes=_json_mapping(record.get("node_attributes", {})),
            )
            nodes.append(node)
            node_by_event_id[event_id] = node_id
            if record.get("parent_event_id"):
                parent_by_event_id[event_id] = str(record["parent_event_id"])
        for event_id, parent_event_id in parent_by_event_id.items():
            if parent_event_id not in node_by_event_id:
                continue
            relations.append(
                ExecutionRelation(
                    relation_id=stable_id("relation.event.parent", parent_event_id, event_id),
                    kind=RelationKind.PARENT_OF,
                    source_ref=node_by_event_id[parent_event_id],
                    target_ref=node_by_event_id[event_id],
                    derivation=DerivationKind.EXPLICIT,
                )
            )
        return CollectionFragment(
            fragment_id=stable_id("fragment.events", request.request_id, len(records)),
            adapter_id=self.adapter_id,
            sources=(source,),
            components=tuple(sorted(components.values(), key=lambda item: item.component_id)),
            nodes=tuple(sorted(nodes, key=lambda item: item.node_id)),
            relations=tuple(sorted(relations, key=lambda item: item.relation_id)),
            observations=tuple(sorted(observations, key=lambda item: item.observation_id)),
        )


def _flatten_otel_records(records: Iterable[Mapping[str, Any]]) -> Iterable[dict[str, Any]]:
    for item in records:
        if "resourceSpans" not in item:
            yield dict(item)
            continue
        for resource_span in item.get("resourceSpans", []):
            resource = _as_mapping(resource_span.get("resource", {}))
            resource_attributes = _decode_otel_attributes(resource.get("attributes", []))
            for scope_span in resource_span.get("scopeSpans", resource_span.get("instrumentationLibrarySpans", [])):
                for span in scope_span.get("spans", []):
                    value = dict(span)
                    value["resource_attributes"] = resource_attributes
                    value["attributes"] = _decode_otel_attributes(span.get("attributes", []))
                    yield value


def _decode_otel_attributes(values: Any) -> dict[str, Any]:
    if isinstance(values, Mapping):
        return dict(values)
    result: dict[str, Any] = {}
    if not isinstance(values, list):
        return result
    for item in values:
        if not isinstance(item, Mapping) or "key" not in item:
            continue
        raw_value = item.get("value")
        if isinstance(raw_value, Mapping):
            for key in ("stringValue", "intValue", "doubleValue", "boolValue", "arrayValue"):
                if key in raw_value:
                    raw_value = raw_value[key]
                    break
        result[str(item["key"])] = raw_value
    return result


def _attributes(record: Mapping[str, Any]) -> dict[str, Any]:
    return _decode_otel_attributes(record.get("attributes", {}))


def _otel_time(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    return parse_timestamp(value)


def _status(record: Mapping[str, Any]) -> str:
    status = record.get("status")
    if isinstance(status, Mapping):
        code = status.get("code") or status.get("statusCode")
        return str(code or "unknown").lower()
    return str(status or "unknown").lower()


def _node_kind(record: Mapping[str, Any], attrs: Mapping[str, Any]) -> NodeKind:
    name = str(record.get("name") or "").lower()
    span_kind = str(record.get("kind") or "").lower()
    messaging_operation = str(attrs.get("messaging.operation") or "").lower()
    db_system = attrs.get("db.system")
    if db_system:
        statement = str(attrs.get("db.statement") or name).lower()
        if statement.startswith(("select", "get", "read")):
            return NodeKind.READ
        if statement.startswith(("insert", "update", "delete", "write")):
            return NodeKind.WRITE
        return NodeKind.QUERY
    if messaging_operation in {"publish", "send"} or "publish" in name:
        return NodeKind.MESSAGE_PUBLISH
    if messaging_operation in {"receive", "process"} or "task" in name or "consume" in name:
        return NodeKind.TASK_ATTEMPT
    if "client" in span_kind:
        return NodeKind.EXTERNAL_REQUEST
    if "server" in span_kind or attrs.get("http.route"):
        return NodeKind.REQUEST_HANDLER
    return NodeKind.SERVICE_OPERATION


def _component_kind(service_name: str, attrs: Mapping[str, Any]) -> ComponentKind:
    role = str(attrs.get("service.role") or "").lower()
    name = service_name.lower()
    if "worker" in role or "worker" in name:
        return ComponentKind.WORKER
    if "frontend" in role or "browser" in name or "web" in name:
        return ComponentKind.FRONTEND
    if "database" in role or "postgres" in name or "mysql" in name:
        return ComponentKind.DATABASE
    if "api" in role or "api" in name:
        return ComponentKind.API
    return ComponentKind.SERVICE


def _boundary_kind(node_kind: NodeKind) -> BoundaryKind:
    if node_kind in {NodeKind.MESSAGE_CONSUME, NodeKind.TASK_ATTEMPT}:
        return BoundaryKind.MESSAGE_CONSUME
    if node_kind in {NodeKind.QUERY, NodeKind.READ, NodeKind.WRITE, NodeKind.TRANSACTION}:
        return BoundaryKind.DATABASE
    return BoundaryKind.HTTP


def _as_mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _json_mapping(value: Any) -> dict[str, Any]:
    return {str(key): item for key, item in _as_mapping(value).items()}


def _optional_string(value: Any) -> str | None:
    if value in (None, ""):
        return None
    return str(value)


def _optional_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    return int(value)
