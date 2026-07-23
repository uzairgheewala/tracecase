from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import Field, JsonValue, field_validator

from tracecase_model import TracecaseModel
from tracecase_model.types import CanonicalId


class BundleProfile(StrEnum):
    EVIDENCE = "evidence"
    ANALYZED = "analyzed"
    SHAREABLE = "shareable"
    REPRODUCIBLE = "reproducible"
    SYNTHETIC_BENCHMARK = "synthetic_benchmark"
    COMPARISON = "comparison"


class BundleLifecycle(StrEnum):
    DRAFT = "draft"
    FROZEN = "frozen"
    VERIFIED = "verified"
    SIGNED = "signed"


class ProducerDescriptor(TracecaseModel):
    name: str
    version: str


class PrivacyDescriptor(TracecaseModel):
    classification: str = "internal"
    redaction_policy_ref: str | None = None
    validation_ref: str | None = None


class AnalysisDescriptor(TracecaseModel):
    status: str = "not_started"
    analysis_runs_ref: str | None = None


class ScenarioDescriptor(TracecaseModel):
    family_ref: str | None = None
    definition_ref: str | None = None
    instance_ref: str | None = None
    expectations_ref: str | None = None


class CollectionDescriptor(TracecaseModel):
    status: str = "not_collected"
    request_ref: str | None = None
    result_ref: str | None = None


class IntegrityDescriptor(TracecaseModel):
    evidence_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    bundle_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    signature_ref: str | None = None


class BundleManifest(TracecaseModel):
    format: str = "tracecase.bundle"
    format_version: str = "1.0.0"
    bundle_id: CanonicalId
    case_id: CanonicalId
    case_version: int = Field(default=1, ge=1)
    case_category: str
    profiles: tuple[BundleProfile, ...]
    lifecycle: BundleLifecycle
    created_at: datetime
    frozen_at: datetime | None = None
    producer: ProducerDescriptor
    roots: tuple[dict[str, str], ...] = ()
    baselines: tuple[CanonicalId, ...] = ()
    schema_catalog_ref: str = "schemas/schema_catalog.json"
    content_index_ref: str = "integrity/content_index.json"
    checksums_ref: str = "integrity/checksums.json"
    case_ref: str = "specification/case.json"
    privacy: PrivacyDescriptor = Field(default_factory=PrivacyDescriptor)
    analysis: AnalysisDescriptor = Field(default_factory=AnalysisDescriptor)
    scenario: ScenarioDescriptor | None = None
    collection: CollectionDescriptor = Field(default_factory=CollectionDescriptor)
    integrity: IntegrityDescriptor

    @field_validator("created_at", "frozen_at")
    @classmethod
    def timestamps_must_be_aware(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("manifest timestamps must be timezone-aware")
        return value


class ContentEntry(TracecaseModel):
    path: str
    media_type: str
    size_bytes: int = Field(ge=0)
    digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    layer: str
    required: bool = True


class ContentIndex(TracecaseModel):
    index_version: str = "1.0.0"
    entries: tuple[ContentEntry, ...]


class DerivedArtifactMetadata(TracecaseModel):
    artifact_id: CanonicalId
    artifact_kind: str
    producer: ProducerDescriptor
    configuration_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    input_evidence_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    parent_artifact_refs: tuple[CanonicalId, ...] = ()
    generated_at: datetime
    determinism_class: str
    output_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")


class ValidationIssue(TracecaseModel):
    severity: str
    code: str
    message: str
    path: str | None = None
    details: dict[str, JsonValue] = Field(default_factory=dict)


class ValidationReport(TracecaseModel):
    valid: bool
    checked_at: datetime
    issues: tuple[ValidationIssue, ...] = ()
