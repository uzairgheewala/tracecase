from __future__ import annotations

from enum import StrEnum

from pydantic import Field, JsonValue

from tracecase_model import (
    Confidence,
    DerivationKind,
    ExecutionNode,
    ExecutionRelation,
    TemporalRelationKind,
    TracecaseModel,
)
from tracecase_model.types import CanonicalId, Namespace


class IdentityGroupKind(StrEnum):
    TRACE = "trace"
    WORKFLOW = "workflow"
    LOGICAL_OPERATION = "logical_operation"
    TASK = "task"
    MESSAGE = "message"
    TRANSACTION = "transaction"
    TENANT = "tenant"
    IDEMPOTENCY_SCOPE = "idempotency_scope"


class IdentityGroup(TracecaseModel):
    group_id: CanonicalId
    kind: IdentityGroupKind
    identity_value: str
    member_node_refs: tuple[CanonicalId, ...]
    attributes: dict[str, JsonValue] = Field(default_factory=dict)


class ContextFlowStatus(StrEnum):
    PRESERVED = "preserved"
    MUTATED = "mutated"
    REGENERATED = "regenerated"
    UNKNOWN = "unknown"


class ContextFlow(TracecaseModel):
    flow_id: CanonicalId
    qualified_name: str
    source_context_ref: CanonicalId
    target_context_ref: CanonicalId
    source_node_ref: CanonicalId
    target_node_ref: CanonicalId
    status: ContextFlowStatus
    derivation: DerivationKind
    confidence: Confidence = Confidence(score=1.0)
    attributes: dict[str, JsonValue] = Field(default_factory=dict)


class EffectGroup(TracecaseModel):
    group_id: CanonicalId
    logical_effect_key: str
    member_effect_refs: tuple[CanonicalId, ...]
    durable_count: int = Field(ge=0)
    idempotency_keys: tuple[str, ...] = ()
    attributes: dict[str, JsonValue] = Field(default_factory=dict)


class TemporalConstraint(TracecaseModel):
    constraint_id: CanonicalId
    source_node_ref: CanonicalId
    target_node_ref: CanonicalId
    kind: TemporalRelationKind
    derivation: DerivationKind
    confidence: Confidence
    rationale: str
    relation_ref: CanonicalId | None = None
    attributes: dict[str, JsonValue] = Field(default_factory=dict)


class GraphAssemblyWarning(TracecaseModel):
    warning_id: CanonicalId
    code: str
    message: str
    node_refs: tuple[CanonicalId, ...] = ()
    relation_refs: tuple[CanonicalId, ...] = ()
    attributes: dict[str, JsonValue] = Field(default_factory=dict)


class GraphAssemblyReport(TracecaseModel):
    assembler_id: str = "tracecase.graph-assembler"
    assembler_version: str = "0.3.0"
    source_relation_count: int = Field(ge=0)
    derived_relation_count: int = Field(ge=0)
    identity_group_count: int = Field(ge=0)
    context_flow_count: int = Field(ge=0)
    effect_group_count: int = Field(ge=0)
    temporal_constraint_count: int = Field(ge=0)
    disconnected_components: tuple[tuple[CanonicalId, ...], ...] = ()
    warnings: tuple[GraphAssemblyWarning, ...] = ()
    attributes: dict[str, JsonValue] = Field(default_factory=dict)


class AssembledExecutionGraph(TracecaseModel):
    graph_id: CanonicalId
    execution_id: CanonicalId
    nodes: tuple[ExecutionNode, ...]
    relations: tuple[ExecutionRelation, ...]
    source_relation_refs: tuple[CanonicalId, ...]
    derived_relation_refs: tuple[CanonicalId, ...]
    identity_groups: tuple[IdentityGroup, ...]
    context_flows: tuple[ContextFlow, ...]
    effect_groups: tuple[EffectGroup, ...]
    temporal_constraints: tuple[TemporalConstraint, ...]
    report: GraphAssemblyReport
    extensions: dict[Namespace, JsonValue] = Field(default_factory=dict)


class TimelineEntry(TracecaseModel):
    entry_id: CanonicalId
    node_ref: CanonicalId
    component_ref: CanonicalId
    operation: str
    node_kind: str
    status: str
    start_offset_ms: float
    duration_ms: float
    uncertainty_ms: float = 0.0
    attempt: int | None = None
    attributes: dict[str, JsonValue] = Field(default_factory=dict)


class TimelineLane(TracecaseModel):
    lane_id: CanonicalId
    component_ref: CanonicalId
    label: str
    entries: tuple[TimelineEntry, ...]


class TimelineConnector(TracecaseModel):
    connector_id: CanonicalId
    relation_ref: CanonicalId
    source_entry_ref: CanonicalId
    target_entry_ref: CanonicalId
    relation_kind: str
    derivation: DerivationKind


class TimelineModel(TracecaseModel):
    timeline_id: CanonicalId
    execution_id: CanonicalId
    origin_timestamp: str
    total_duration_ms: float
    lanes: tuple[TimelineLane, ...]
    connectors: tuple[TimelineConnector, ...]
    warnings: tuple[GraphAssemblyWarning, ...] = ()
