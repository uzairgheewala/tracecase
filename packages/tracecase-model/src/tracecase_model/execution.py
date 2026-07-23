from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import Field, JsonValue, field_validator, model_validator

from .base import TracecaseModel
from .types import (
    CanonicalId,
    Confidence,
    DerivationKind,
    EvidenceClassification,
    Namespace,
    PropagationContract,
    ProvenanceRef,
    SensitivityLabel,
    TemporalRelationKind,
    TimeObservation,
)


class NodeKind(StrEnum):
    USER_ACTION = "user_action"
    UI_EVENT = "ui_event"
    NAVIGATION = "navigation"
    CLIENT_REQUEST = "client_request"
    CLIENT_CALLBACK = "client_callback"
    REQUEST_HANDLER = "request_handler"
    SERVICE_OPERATION = "service_operation"
    DOMAIN_OPERATION = "domain_operation"
    MIDDLEWARE_OPERATION = "middleware_operation"
    AUTHORIZATION_CHECK = "authorization_check"
    VALIDATION_OPERATION = "validation_operation"
    MESSAGE_PUBLISH = "message_publish"
    MESSAGE_DELIVERY = "message_delivery"
    MESSAGE_CONSUME = "message_consume"
    TASK_ATTEMPT = "task_attempt"
    RETRY_SCHEDULE = "retry_schedule"
    TIMER_FIRE = "timer_fire"
    BATCH_ITEM = "batch_item"
    WORKFLOW_STEP = "workflow_step"
    TRANSACTION = "transaction"
    QUERY = "query"
    READ = "read"
    WRITE = "write"
    LOCK_ACQUIRE = "lock_acquire"
    LOCK_RELEASE = "lock_release"
    CACHE_READ = "cache_read"
    CACHE_WRITE = "cache_write"
    CACHE_INVALIDATE = "cache_invalidate"
    EXTERNAL_REQUEST = "external_request"
    EXTERNAL_RESPONSE = "external_response"
    NOTIFICATION = "notification"
    FILE_WRITE = "file_write"
    OBJECT_UPLOAD = "object_upload"
    DOMAIN_EFFECT = "domain_effect"
    PROCESS_START = "process_start"
    DEPLOYMENT = "deployment"
    CONFIGURATION_LOAD = "configuration_load"
    FEATURE_FLAG_EVALUATION = "feature_flag_evaluation"
    RESOURCE_WAIT = "resource_wait"
    RESOURCE_ALLOCATION = "resource_allocation"
    UNKNOWN_OPERATION = "unknown_operation"


class RelationKind(StrEnum):
    CONTAINS = "contains"
    PARENT_OF = "parent_of"
    PART_OF_WORKFLOW = "part_of_workflow"
    PART_OF_ATTEMPT = "part_of_attempt"
    PART_OF_TRANSACTION = "part_of_transaction"
    INVOKES = "invokes"
    RETURNS_TO = "returns_to"
    SPAWNS = "spawns"
    SCHEDULES = "schedules"
    PUBLISHES = "publishes"
    DELIVERS = "delivers"
    CONSUMES = "consumes"
    RETRIES = "retries"
    COMPENSATES = "compensates"
    CANCELS = "cancels"
    PRODUCES = "produces"
    CONSUMES_DATA = "consumes_data"
    READS_FROM = "reads_from"
    WRITES_TO = "writes_to"
    DERIVED_FROM = "derived_from"
    INVALIDATES = "invalidates"
    OBSERVES_STATE = "observes_state"
    SAME_TRACE = "same_trace"
    SAME_WORKFLOW = "same_workflow"
    SAME_LOGICAL_OPERATION = "same_logical_operation"
    SAME_TASK = "same_task"
    SAME_ATTEMPT = "same_attempt"
    SAME_MESSAGE = "same_message"
    SAME_IDEMPOTENCY_SCOPE = "same_idempotency_scope"
    SAME_TENANT = "same_tenant"
    SAME_USER_SESSION = "same_user_session"
    PRODUCES_EFFECT = "produces_effect"
    REPEATS_EFFECT = "repeats_effect"
    REVERSES_EFFECT = "reverses_effect"
    PARTIALLY_REVERSES_EFFECT = "partially_reverses_effect"
    DEPENDS_ON_EFFECT = "depends_on_effect"
    CONFLICTS_WITH_EFFECT = "conflicts_with_effect"
    HAPPENS_BEFORE = "happens_before"
    HAPPENS_AFTER = "happens_after"
    OVERLAPS = "overlaps"
    POSSIBLY_CONCURRENT = "possibly_concurrent"
    ORDERING_UNKNOWN = "ordering_unknown"
    TIMESTAMP_CONFLICT = "timestamp_conflict"


class ObservationKind(StrEnum):
    SPAN = "span"
    LOG = "log"
    EXCEPTION = "exception"
    METRIC_SAMPLE = "metric_sample"
    SQL_EVENT = "sql_event"
    HTTP_EVENT = "http_event"
    TASK_EVENT = "task_event"
    FRONTEND_EVENT = "frontend_event"
    DOMAIN_EVENT = "domain_event"
    DEPLOYMENT_EVENT = "deployment_event"
    CONFIGURATION_EVENT = "configuration_event"
    SYNTHETIC_ORACLE = "synthetic_oracle"
    HUMAN_ANNOTATION = "human_annotation"


class EffectKind(StrEnum):
    STATE_CREATE = "state_create"
    STATE_UPDATE = "state_update"
    STATE_DELETE = "state_delete"
    MESSAGE_EMIT = "message_emit"
    NOTIFICATION_SEND = "notification_send"
    EXTERNAL_MUTATION = "external_mutation"
    CACHE_MUTATION = "cache_mutation"
    FILE_MUTATION = "file_mutation"
    AUTHORIZATION_CHANGE = "authorization_change"
    RESOURCE_ALLOCATION = "resource_allocation"
    DOMAIN_EFFECT = "domain_effect"
    UNKNOWN_EFFECT = "unknown_effect"


class EffectDurability(StrEnum):
    ATTEMPTED = "attempted"
    ACKNOWLEDGED = "acknowledged"
    COMMITTED = "committed"
    DURABLE = "durable"
    UNKNOWN = "unknown"
    REVERSED = "reversed"


class ExecutionIdentitySet(TracecaseModel):
    trace_id: str | None = None
    span_id: str | None = None
    parent_span_id: str | None = None
    request_id: str | None = None
    session_id: str | None = None
    workflow_id: str | None = None
    run_id: str | None = None
    logical_operation_id: str | None = None
    operation_attempt_id: str | None = None
    task_id: str | None = None
    task_root_id: str | None = None
    task_parent_id: str | None = None
    task_attempt: int | None = Field(default=None, ge=0)
    message_id: str | None = None
    delivery_id: str | None = None
    idempotency_key: str | None = None
    transaction_id: str | None = None
    tenant_id: str | None = None
    principal_id: str | None = None
    entity_refs: dict[str, str] = Field(default_factory=dict)
    extensions: dict[Namespace, JsonValue] = Field(default_factory=dict)


class ContextField(TracecaseModel):
    context_id: CanonicalId
    namespace: str
    field_name: str
    value: JsonValue
    propagation_contract: PropagationContract
    origin_node_ref: CanonicalId | None = None
    observed_at_node_ref: CanonicalId | None = None
    sensitivity: set[SensitivityLabel] = Field(default_factory=set)
    redaction_action: str | None = None
    extensions: dict[Namespace, JsonValue] = Field(default_factory=dict)

    @property
    def qualified_name(self) -> str:
        return f"{self.namespace}.{self.field_name}"


class Observation(TracecaseModel):
    observation_id: CanonicalId
    kind: ObservationKind
    provenance: ProvenanceRef
    captured_at: datetime
    event_time: TimeObservation | None = None
    normalized_refs: tuple[CanonicalId, ...] = ()
    attributes: dict[str, JsonValue] = Field(default_factory=dict)
    sensitivity: set[SensitivityLabel] = Field(default_factory=set)
    redaction_status: str | None = None
    extensions: dict[Namespace, JsonValue] = Field(default_factory=dict)

    @field_validator("captured_at")
    @classmethod
    def captured_at_must_be_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("captured_at must be timezone-aware")
        return value


class StateFact(TracecaseModel):
    fact_id: CanonicalId
    subject_ref: CanonicalId
    property_name: str
    value: JsonValue
    valid_time: TimeObservation | None = None
    observed_time: TimeObservation
    observation_ref: CanonicalId
    transaction_ref: CanonicalId | None = None
    confidence: Confidence = Confidence(score=1.0, rationale="recorded fact")
    sensitivity: set[SensitivityLabel] = Field(default_factory=set)
    extensions: dict[Namespace, JsonValue] = Field(default_factory=dict)


class Effect(TracecaseModel):
    effect_id: CanonicalId
    kind: EffectKind
    logical_effect_key: str
    producer_node_ref: CanonicalId
    target_resource_ref: CanonicalId | None = None
    operation: str
    before_digest: str | None = Field(default=None, pattern=r"^sha256:[0-9a-f]{64}$")
    after_digest: str | None = Field(default=None, pattern=r"^sha256:[0-9a-f]{64}$")
    transaction_ref: CanonicalId | None = None
    idempotency_key: str | None = None
    durability: EffectDurability = EffectDurability.UNKNOWN
    reversibility: str | None = None
    completion_status: str | None = None
    evidence_refs: tuple[CanonicalId, ...] = ()
    sensitivity: set[SensitivityLabel] = Field(default_factory=set)
    attributes: dict[str, JsonValue] = Field(default_factory=dict)
    extensions: dict[Namespace, JsonValue] = Field(default_factory=dict)


class ExecutionNode(TracecaseModel):
    node_id: CanonicalId
    kind: NodeKind
    operation: str
    component_ref: CanonicalId
    boundary_refs: tuple[CanonicalId, ...] = ()
    identities: ExecutionIdentitySet = Field(default_factory=ExecutionIdentitySet)
    context_refs: tuple[CanonicalId, ...] = ()
    timing: TimeObservation
    end_time: TimeObservation | None = None
    status: str = "unknown"
    inputs: dict[str, JsonValue] = Field(default_factory=dict)
    outputs: dict[str, JsonValue] = Field(default_factory=dict)
    state_refs: tuple[CanonicalId, ...] = ()
    effect_refs: tuple[CanonicalId, ...] = ()
    observation_refs: tuple[CanonicalId, ...] = ()
    sensitivity: set[SensitivityLabel] = Field(default_factory=set)
    attributes: dict[str, JsonValue] = Field(default_factory=dict)
    extensions: dict[Namespace, JsonValue] = Field(default_factory=dict)

    @model_validator(mode="after")
    def end_cannot_precede_start_when_same_clock(self) -> "ExecutionNode":
        if self.end_time and self.timing.clock_ref == self.end_time.clock_ref:
            if self.end_time.effective_timestamp < self.timing.effective_timestamp:
                raise ValueError("end_time cannot precede timing on the same normalized clock")
        return self


class ExecutionRelation(TracecaseModel):
    relation_id: CanonicalId
    kind: RelationKind
    source_ref: CanonicalId
    target_ref: CanonicalId
    derivation: DerivationKind
    evidence_refs: tuple[CanonicalId, ...] = ()
    confidence: Confidence = Confidence(score=1.0)
    temporal_kind: TemporalRelationKind | None = None
    attributes: dict[str, JsonValue] = Field(default_factory=dict)
    extensions: dict[Namespace, JsonValue] = Field(default_factory=dict)


class ExecutionModel(TracecaseModel):
    execution_id: CanonicalId
    nodes: tuple[ExecutionNode, ...] = ()
    relations: tuple[ExecutionRelation, ...] = ()
    contexts: tuple[ContextField, ...] = ()
    state_facts: tuple[StateFact, ...] = ()
    effects: tuple[Effect, ...] = ()
    observations: tuple[Observation, ...] = ()
    evidence_classification: EvidenceClassification = EvidenceClassification.RECORDED
    extensions: dict[Namespace, JsonValue] = Field(default_factory=dict)

    @model_validator(mode="after")
    def graph_references_must_resolve(self) -> "ExecutionModel":
        categories: dict[str, tuple[object, ...]] = {
            "node": self.nodes,
            "relation": self.relations,
            "context": self.contexts,
            "fact": self.state_facts,
            "effect": self.effects,
            "observation": self.observations,
        }
        ids: dict[str, set[str]] = {}
        attr_by_category = {
            "node": "node_id",
            "relation": "relation_id",
            "context": "context_id",
            "fact": "fact_id",
            "effect": "effect_id",
            "observation": "observation_id",
        }
        all_ids: set[str] = set()
        for category, values in categories.items():
            category_ids = {getattr(value, attr_by_category[category]) for value in values}
            if len(category_ids) != len(values):
                raise ValueError(f"{category} IDs must be unique")
            overlap = all_ids & category_ids
            if overlap:
                raise ValueError(f"canonical IDs must be globally unique: {sorted(overlap)}")
            all_ids |= category_ids
            ids[category] = category_ids

        for node in self.nodes:
            self._require_all(node.context_refs, ids["context"], f"node {node.node_id} context")
            self._require_all(node.state_refs, ids["fact"], f"node {node.node_id} state")
            self._require_all(node.effect_refs, ids["effect"], f"node {node.node_id} effect")
            self._require_all(node.observation_refs, ids["observation"], f"node {node.node_id} observation")

        relation_targets = ids["node"] | ids["fact"] | ids["effect"] | ids["observation"]
        for relation in self.relations:
            if relation.source_ref not in relation_targets:
                raise ValueError(f"unknown relation source: {relation.source_ref}")
            if relation.target_ref not in relation_targets:
                raise ValueError(f"unknown relation target: {relation.target_ref}")
            self._require_all(relation.evidence_refs, ids["observation"], f"relation {relation.relation_id} evidence")

        for context in self.contexts:
            for ref in (context.origin_node_ref, context.observed_at_node_ref):
                if ref and ref not in ids["node"]:
                    raise ValueError(f"unknown context node reference: {ref}")

        for fact in self.state_facts:
            if fact.observation_ref not in ids["observation"]:
                raise ValueError(f"unknown fact observation: {fact.observation_ref}")
            if fact.transaction_ref and fact.transaction_ref not in ids["node"]:
                raise ValueError(f"unknown fact transaction: {fact.transaction_ref}")

        for effect in self.effects:
            if effect.producer_node_ref not in ids["node"]:
                raise ValueError(f"unknown effect producer: {effect.producer_node_ref}")
            if effect.transaction_ref and effect.transaction_ref not in ids["node"]:
                raise ValueError(f"unknown effect transaction: {effect.transaction_ref}")
            self._require_all(effect.evidence_refs, ids["observation"], f"effect {effect.effect_id} evidence")
        return self

    @staticmethod
    def _require_all(values: tuple[str, ...], allowed: set[str], label: str) -> None:
        missing = set(values) - allowed
        if missing:
            raise ValueError(f"unknown {label} references: {sorted(missing)}")
