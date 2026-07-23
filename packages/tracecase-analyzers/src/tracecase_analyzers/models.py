from __future__ import annotations

from enum import StrEnum

from pydantic import Field, JsonValue

from tracecase_invariants import InvariantEvaluationReport
from tracecase_model import Confidence, EvidenceClassification, TracecaseModel
from tracecase_model.types import CanonicalId, Namespace


class FindingSeverity(StrEnum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class FindingCategory(StrEnum):
    CONTEXT = "context"
    IDENTITY = "identity"
    RETRY_EFFECT = "retry_effect"
    TRANSACTION_ORDERING = "transaction_ordering"
    OBSERVABILITY = "observability"
    RESOURCE_PERFORMANCE = "resource_performance"
    PRIVACY = "privacy"
    CONTRACT = "contract"


class FindingStatus(StrEnum):
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    SUPPRESSED = "suppressed"
    RESOLVED = "resolved"


class AnalyzerDefinition(TracecaseModel):
    analyzer_id: CanonicalId
    version: str = "0.3.0"
    title: str
    category: FindingCategory
    description: str
    invariant_refs: tuple[CanonicalId, ...]
    deterministic: bool = True
    parameters: dict[str, JsonValue] = Field(default_factory=dict)
    extensions: dict[Namespace, JsonValue] = Field(default_factory=dict)


class Finding(TracecaseModel):
    finding_id: CanonicalId
    analyzer_ref: CanonicalId
    analyzer_version: str
    category: FindingCategory
    classification: str
    title: str
    summary: str
    severity: FindingSeverity
    status: FindingStatus = FindingStatus.OPEN
    evidence_classification: EvidenceClassification
    confidence: Confidence
    related_invariant_result_refs: tuple[CanonicalId, ...] = ()
    evidence_refs: tuple[CanonicalId, ...] = ()
    node_refs: tuple[CanonicalId, ...] = ()
    relation_refs: tuple[CanonicalId, ...] = ()
    context_refs: tuple[CanonicalId, ...] = ()
    effect_refs: tuple[CanonicalId, ...] = ()
    conflicting_evidence_refs: tuple[CanonicalId, ...] = ()
    limitations: tuple[str, ...] = ()
    recommended_inspection_points: tuple[str, ...] = ()
    attributes: dict[str, JsonValue] = Field(default_factory=dict)
    extensions: dict[Namespace, JsonValue] = Field(default_factory=dict)


class AnalyzerRunRecord(TracecaseModel):
    run_id: CanonicalId
    analyzer_ref: CanonicalId
    analyzer_version: str
    input_case_ref: CanonicalId
    input_graph_ref: CanonicalId
    invariant_result_refs: tuple[CanonicalId, ...]
    finding_refs: tuple[CanonicalId, ...]
    deterministic: bool = True
    attributes: dict[str, JsonValue] = Field(default_factory=dict)


class AnalysisReport(TracecaseModel):
    report_id: CanonicalId
    case_id: CanonicalId
    graph_id: CanonicalId
    invariant_report: InvariantEvaluationReport
    analyzer_runs: tuple[AnalyzerRunRecord, ...]
    findings: tuple[Finding, ...]
    summary: dict[str, int]
    limitations: tuple[str, ...] = ()
    deterministic: bool = True
