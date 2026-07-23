from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import Field, JsonValue, field_validator

from .base import TracecaseModel
from .execution import ExecutionModel
from .system import SystemModel
from .types import CanonicalId, LifecycleStatus, Namespace, SourceDescriptor


class CaseCategory(StrEnum):
    OBSERVED_SINGLE = "observed_single"
    OBSERVED_COMPOSITE = "observed_composite"
    SYNTHETIC = "synthetic"
    HYBRID = "hybrid"
    COMPARISON = "comparison"
    REGRESSION = "regression"
    INCIDENT_REVIEW = "incident_review"
    INSTRUMENTATION_AUDIT = "instrumentation_audit"
    PRIVACY_AUDIT = "privacy_audit"


class CaseSpecification(TracecaseModel):
    case_id: CanonicalId
    title: str
    category: CaseCategory
    description: str | None = None
    created_at: datetime
    roots: tuple[dict[str, str], ...] = ()
    collection_scope: dict[str, JsonValue] = Field(default_factory=dict)
    privacy_policy_ref: str | None = None
    scenario_ref: str | None = None
    baseline_case_refs: tuple[CanonicalId, ...] = ()
    extensions: dict[Namespace, JsonValue] = Field(default_factory=dict)

    @field_validator("created_at")
    @classmethod
    def created_at_must_be_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("created_at must be timezone-aware")
        return value


class CaseEvidence(TracecaseModel):
    sources: tuple[SourceDescriptor, ...] = ()
    execution: ExecutionModel
    attachments: tuple[str, ...] = ()
    extensions: dict[Namespace, JsonValue] = Field(default_factory=dict)


class CaseInterpretations(TracecaseModel):
    invariant_results: tuple[dict[str, JsonValue], ...] = ()
    findings: tuple[dict[str, JsonValue], ...] = ()
    limitations: tuple[str, ...] = ()
    annotations: tuple[dict[str, JsonValue], ...] = ()
    extensions: dict[Namespace, JsonValue] = Field(default_factory=dict)


class ExecutionCase(TracecaseModel):
    specification: CaseSpecification
    system: SystemModel
    evidence: CaseEvidence
    interpretations: CaseInterpretations = Field(default_factory=CaseInterpretations)
    lifecycle: LifecycleStatus = LifecycleStatus.DRAFT
    schema_version: str = "1.0.0"
    extensions: dict[Namespace, JsonValue] = Field(default_factory=dict)
