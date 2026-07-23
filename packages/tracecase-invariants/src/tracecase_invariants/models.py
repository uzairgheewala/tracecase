from __future__ import annotations

from enum import StrEnum

from pydantic import Field, JsonValue

from tracecase_model import Confidence, EvidenceClassification, TracecaseModel
from tracecase_model.types import CanonicalId, Namespace


class InvariantClass(StrEnum):
    SAFETY = "safety"
    LIVENESS = "liveness"
    CONTINUITY = "continuity"
    ISOLATION = "isolation"
    ATOMICITY = "atomicity"
    ORDERING = "ordering"
    COMPATIBILITY = "compatibility"
    RESOURCE = "resource"
    OBSERVABILITY = "observability"
    PRIVACY = "privacy"


class InvariantSeverity(StrEnum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class InvariantStatus(StrEnum):
    SATISFIED = "satisfied"
    VIOLATED = "violated"
    INCONCLUSIVE = "inconclusive"
    NOT_APPLICABLE = "not_applicable"
    CONTRADICTED = "contradicted"
    EVALUATION_ERROR = "evaluation_error"


class InsufficientEvidencePolicy(StrEnum):
    INCONCLUSIVE = "inconclusive"
    NOT_APPLICABLE = "not_applicable"
    VIOLATED = "violated"


class ScopeKind(StrEnum):
    CASE = "case"
    EXECUTION = "execution"
    NODE = "node"
    CONTEXT_PATH = "context_path"
    EFFECT_GROUP = "effect_group"
    IDENTITY_GROUP = "identity_group"
    RELATION = "relation"
    RESOURCE = "resource"


class EvaluatorKind(StrEnum):
    CONTEXT_REQUIRED_CONTINUITY = "context.required_continuity"
    CONTEXT_FORBIDDEN_PROPAGATION = "context.forbidden_propagation"
    IDENTITY_EXECUTION_ISOLATION = "identity.execution_isolation"
    IDENTITY_WORKFLOW_CORRELATABLE = "identity.workflow_correlatable"
    EFFECT_AT_MOST_ONCE = "effect.at_most_once"
    EFFECT_REQUIRED_EVENTUALITY = "effect.required_eventuality"
    ORDERING_READ_AFTER_VISIBILITY = "ordering.read_after_visibility"
    CONSISTENCY_REQUIRED_FRESHNESS = "consistency.required_freshness"
    CONTRACT_SCHEMA_COMPATIBLE = "contract.schema_compatible"
    RESOURCE_CAPACITY_BOUNDED = "resource.capacity_bounded"
    PERFORMANCE_WORK_AMPLIFICATION = "performance.work_amplification"
    OBSERVABILITY_REQUIRED_LINKAGE = "observability.required_linkage"
    PRIVACY_PROHIBITED_CAPTURE = "privacy.prohibited_capture"


class EvidenceRequirement(TracecaseModel):
    kind: str
    minimum_count: int = Field(default=1, ge=0)
    description: str | None = None


class ScopeSelector(TracecaseModel):
    kind: ScopeKind = ScopeKind.CASE
    operation_pattern: str | None = None
    node_kinds: tuple[str, ...] = ()
    component_kinds: tuple[str, ...] = ()
    attributes: dict[str, JsonValue] = Field(default_factory=dict)


class InvariantDefinition(TracecaseModel):
    invariant_id: CanonicalId
    version: str = "1.0.0"
    title: str
    description: str
    invariant_class: InvariantClass
    evaluator_kind: EvaluatorKind
    severity: InvariantSeverity = InvariantSeverity.MEDIUM
    scope: ScopeSelector = Field(default_factory=ScopeSelector)
    parameters: dict[str, JsonValue] = Field(default_factory=dict)
    required_evidence: tuple[EvidenceRequirement, ...] = ()
    insufficient_evidence_policy: InsufficientEvidencePolicy = InsufficientEvidencePolicy.INCONCLUSIVE
    tags: tuple[str, ...] = ()
    extensions: dict[Namespace, JsonValue] = Field(default_factory=dict)


class EvaluationTraceStep(TracecaseModel):
    step_id: CanonicalId
    operation: str
    outcome: str
    message: str
    input_refs: tuple[CanonicalId, ...] = ()
    attributes: dict[str, JsonValue] = Field(default_factory=dict)


class InvariantResult(TracecaseModel):
    result_id: CanonicalId
    invariant_ref: CanonicalId
    invariant_version: str
    scope_kind: ScopeKind
    scope_ref: str
    status: InvariantStatus
    severity: InvariantSeverity
    evidence_classification: EvidenceClassification
    evidence_refs: tuple[CanonicalId, ...] = ()
    node_refs: tuple[CanonicalId, ...] = ()
    relation_refs: tuple[CanonicalId, ...] = ()
    context_refs: tuple[CanonicalId, ...] = ()
    effect_refs: tuple[CanonicalId, ...] = ()
    counterexample_refs: tuple[CanonicalId, ...] = ()
    missing_evidence: tuple[str, ...] = ()
    confidence: Confidence = Confidence(score=1.0)
    explanation: str
    evaluation_trace: tuple[EvaluationTraceStep, ...] = ()
    attributes: dict[str, JsonValue] = Field(default_factory=dict)
    extensions: dict[Namespace, JsonValue] = Field(default_factory=dict)


class InvariantEvaluationReport(TracecaseModel):
    report_id: CanonicalId
    runtime_id: str = "tracecase.invariant-runtime"
    runtime_version: str = "0.3.0"
    case_id: CanonicalId
    execution_id: CanonicalId
    graph_id: CanonicalId
    definition_refs: tuple[CanonicalId, ...]
    results: tuple[InvariantResult, ...]
    summary: dict[InvariantStatus, int]
    deterministic: bool = True
    attributes: dict[str, JsonValue] = Field(default_factory=dict)
