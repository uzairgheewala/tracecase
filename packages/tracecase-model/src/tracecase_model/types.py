from __future__ import annotations

from datetime import datetime, timedelta, timezone
from enum import StrEnum
from typing import Annotated

from pydantic import Field, JsonValue, field_validator, model_validator

from .base import TracecaseModel

CanonicalId = Annotated[str, Field(min_length=3, max_length=160, pattern=r"^[a-z][a-z0-9._:-]*$")]
SchemaVersion = Annotated[str, Field(pattern=r"^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$")]
Namespace = Annotated[str, Field(pattern=r"^[a-z][a-z0-9]*(?:\.[a-z][a-z0-9_-]*)+$")]


class EvidenceClassification(StrEnum):
    RECORDED = "recorded"
    DETERMINISTIC = "deterministic"
    HEURISTIC = "heuristic"
    HUMAN_ASSERTED = "human_asserted"
    UNKNOWN = "unknown"
    CONTRADICTED = "contradicted"


class DerivationKind(StrEnum):
    EXPLICIT = "explicit"
    SOURCE_NATIVE = "source_native"
    DETERMINISTIC = "deterministic"
    HEURISTIC = "heuristic"
    HUMAN_ASSERTED = "human_asserted"


class SensitivityLabel(StrEnum):
    PUBLIC = "public"
    INTERNAL = "internal"
    TENANT_IDENTIFIER = "tenant_identifier"
    USER_IDENTIFIER = "user_identifier"
    STUDENT_RECORD = "student_record"
    CREDENTIAL = "credential"
    FREE_TEXT = "free_text"
    NETWORK_METADATA = "network_metadata"
    QUERY_TEXT = "query_text"
    PAYLOAD_DERIVED = "payload_derived"


class PropagationContract(StrEnum):
    REQUIRED = "required"
    OPTIONAL = "optional"
    FORBIDDEN = "forbidden"
    REGENERATED = "regenerated"
    TRANSLATED = "translated"
    SCOPED = "scoped"
    TERMINAL = "terminal"


class LifecycleStatus(StrEnum):
    DRAFT = "draft"
    COLLECTING = "collecting"
    COLLECTED = "collected"
    NORMALIZED = "normalized"
    CLASSIFIED = "classified"
    REDACTED = "redacted"
    FROZEN = "frozen"
    ANALYZED = "analyzed"
    RENDERED = "rendered"
    VERIFIED = "verified"
    SIGNED = "signed"


class TemporalRelationKind(StrEnum):
    HAPPENS_BEFORE = "happens_before"
    HAPPENS_AFTER = "happens_after"
    OVERLAPS = "overlaps"
    POSSIBLY_CONCURRENT = "possibly_concurrent"
    ORDERING_UNKNOWN = "ordering_unknown"
    TIMESTAMP_CONFLICT = "timestamp_conflict"


class Confidence(TracecaseModel):
    score: Annotated[float, Field(ge=0.0, le=1.0)]
    rationale: str | None = None


class TimeObservation(TracecaseModel):
    raw_timestamp: datetime
    normalized_timestamp: datetime | None = None
    clock_ref: CanonicalId | None = None
    precision_ns: Annotated[int, Field(ge=0)] | None = None
    uncertainty: timedelta = timedelta(0)
    normalization_method: str | None = None

    @field_validator("raw_timestamp", "normalized_timestamp")
    @classmethod
    def timestamps_must_be_aware(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("timestamps must be timezone-aware")
        return value

    @field_validator("uncertainty")
    @classmethod
    def uncertainty_must_be_nonnegative(cls, value: timedelta) -> timedelta:
        if value < timedelta(0):
            raise ValueError("uncertainty cannot be negative")
        return value

    @property
    def effective_timestamp(self) -> datetime:
        return self.normalized_timestamp or self.raw_timestamp.astimezone(timezone.utc)


class SourceDescriptor(TracecaseModel):
    source_id: CanonicalId
    source_kind: str
    name: str
    schema_ref: str | None = None
    location: str | None = None
    captured_at: datetime
    attributes: dict[str, JsonValue] = Field(default_factory=dict)
    extensions: dict[Namespace, JsonValue] = Field(default_factory=dict)

    @field_validator("captured_at")
    @classmethod
    def captured_at_must_be_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("captured_at must be timezone-aware")
        return value


class ProvenanceRef(TracecaseModel):
    source_id: CanonicalId
    source_native_id: str | None = None
    source_location: str | None = None
    source_schema: str | None = None
    payload_digest: str | None = Field(default=None, pattern=r"^sha256:[0-9a-f]{64}$")


class TypedAttribute(TracecaseModel):
    value: JsonValue
    value_type: str | None = None
    unit: str | None = None


class ExtensionCarrier(TracecaseModel):
    extensions: dict[Namespace, JsonValue] = Field(default_factory=dict)

    @model_validator(mode="after")
    def extension_namespaces_cannot_shadow_core(self) -> "ExtensionCarrier":
        for namespace in self.extensions:
            if namespace.startswith("tracecase.core"):
                raise ValueError("extensions cannot use the reserved tracecase.core namespace")
        return self
