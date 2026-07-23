from __future__ import annotations

from enum import StrEnum

from pydantic import Field, JsonValue

from tracecase_model import Confidence, EvidenceClassification, TracecaseModel
from tracecase_model.types import CanonicalId, Namespace


class CaseRole(StrEnum):
    BASELINE = "baseline"
    CANDIDATE = "candidate"
    COUNTERFACTUAL = "counterfactual"
    REPLAY = "replay"
    FIXED = "fixed"
    DEGRADED = "degraded"


class AlignmentStatus(StrEnum):
    ALIGNED = "aligned"
    BASELINE_ONLY = "baseline_only"
    CANDIDATE_ONLY = "candidate_only"
    AMBIGUOUS = "ambiguous"


class ComparisonDimension(StrEnum):
    STRUCTURE = "structure"
    IDENTITY = "identity"
    CONTEXT = "context"
    TIMING = "timing"
    STATE = "state"
    EFFECT = "effect"
    ERROR = "error"
    RESOURCE = "resource"
    DEPLOYMENT = "deployment"
    EVIDENCE = "evidence"


class DivergenceSeverity(StrEnum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class DivergenceConsequence(StrEnum):
    NOISE = "noise"
    OBSERVATIONAL = "observational"
    SEMANTIC = "semantic"
    OUTCOME_RELEVANT = "outcome_relevant"


class NodeSignature(TracecaseModel):
    node_ref: CanonicalId
    node_kind: str
    normalized_operation: str
    component_kind: str
    component_role: str | None = None
    topology_role: str | None = None
    logical_operation_id: str | None = None
    task_name: str | None = None
    stage: int | None = None
    attributes: dict[str, JsonValue] = Field(default_factory=dict)


class NodeAlignment(TracecaseModel):
    alignment_id: CanonicalId
    baseline_node_ref: CanonicalId | None = None
    candidate_node_ref: CanonicalId | None = None
    status: AlignmentStatus
    score: float = Field(ge=0.0, le=1.0)
    confidence: Confidence
    reasons: tuple[str, ...] = ()
    baseline_signature: NodeSignature | None = None
    candidate_signature: NodeSignature | None = None
    ambiguous_candidate_refs: tuple[CanonicalId, ...] = ()
    attributes: dict[str, JsonValue] = Field(default_factory=dict)


class Divergence(TracecaseModel):
    divergence_id: CanonicalId
    dimension: ComparisonDimension
    classification: str
    title: str
    summary: str
    severity: DivergenceSeverity
    consequence: DivergenceConsequence
    evidence_classification: EvidenceClassification
    confidence: Confidence
    alignment_ref: CanonicalId | None = None
    baseline_refs: tuple[CanonicalId, ...] = ()
    candidate_refs: tuple[CanonicalId, ...] = ()
    baseline_evidence_refs: tuple[CanonicalId, ...] = ()
    candidate_evidence_refs: tuple[CanonicalId, ...] = ()
    temporal_rank_ms: float | None = None
    consequential: bool = True
    limitations: tuple[str, ...] = ()
    attributes: dict[str, JsonValue] = Field(default_factory=dict)
    extensions: dict[Namespace, JsonValue] = Field(default_factory=dict)


class ComparisonCaseRef(TracecaseModel):
    role: CaseRole
    case_id: CanonicalId
    graph_id: CanonicalId
    evidence_digest: str | None = None


class ComparisonSummary(TracecaseModel):
    aligned_nodes: int = Field(ge=0)
    baseline_only_nodes: int = Field(ge=0)
    candidate_only_nodes: int = Field(ge=0)
    ambiguous_alignments: int = Field(ge=0)
    divergence_count: int = Field(ge=0)
    consequential_divergence_count: int = Field(ge=0)
    by_dimension: dict[ComparisonDimension, int] = Field(default_factory=dict)
    first_meaningful_divergence_ref: CanonicalId | None = None


class SemanticComparison(TracecaseModel):
    comparison_id: CanonicalId
    engine_id: str = "tracecase.semantic-comparison"
    engine_version: str = "0.3.0"
    baseline: ComparisonCaseRef
    candidate: ComparisonCaseRef
    alignments: tuple[NodeAlignment, ...]
    divergences: tuple[Divergence, ...]
    first_meaningful_divergence_ref: CanonicalId | None = None
    summary: ComparisonSummary
    deterministic: bool = True
    configuration: dict[str, JsonValue] = Field(default_factory=dict)
    limitations: tuple[str, ...] = ()
