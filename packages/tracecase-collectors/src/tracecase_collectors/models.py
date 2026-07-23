from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import Field, JsonValue, field_validator, model_validator

from tracecase_model import (
    Boundary,
    Component,
    ContextField,
    Effect,
    ExecutionNode,
    ExecutionRelation,
    Observation,
    Resource,
    SourceDescriptor,
    StateFact,
    TracecaseModel,
)
from tracecase_model.types import CanonicalId, Namespace


class DiagnosticSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class CollectionSelector(TracecaseModel):
    kind: str
    value: str
    attributes: dict[str, JsonValue] = Field(default_factory=dict)


class CollectionRequest(TracecaseModel):
    request_id: CanonicalId
    selectors: tuple[CollectionSelector, ...]
    start_time: datetime | None = None
    end_time: datetime | None = None
    tenant_scope: str | None = None
    source_options: dict[str, JsonValue] = Field(default_factory=dict)
    attributes: dict[str, JsonValue] = Field(default_factory=dict)

    @field_validator("start_time", "end_time")
    @classmethod
    def times_must_be_aware(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("collection times must be timezone-aware")
        return value

    @model_validator(mode="after")
    def interval_must_be_ordered(self) -> "CollectionRequest":
        if self.start_time and self.end_time and self.end_time < self.start_time:
            raise ValueError("end_time cannot precede start_time")
        return self


class CandidateRecord(TracecaseModel):
    candidate_id: CanonicalId
    adapter_id: CanonicalId
    source_native_id: str
    event_time: datetime | None = None
    relevance_score: float = Field(default=1.0, ge=0.0, le=1.0)
    summary: str | None = None
    attributes: dict[str, JsonValue] = Field(default_factory=dict)


class RawRecord(TracecaseModel):
    record_id: CanonicalId
    adapter_id: CanonicalId
    source_native_id: str
    payload: JsonValue
    event_time: datetime | None = None
    tenant_id: str | None = None
    schema_ref: str | None = None
    sensitivity_hints: tuple[str, ...] = ()
    attributes: dict[str, JsonValue] = Field(default_factory=dict)


class AdapterDiagnostic(TracecaseModel):
    diagnostic_id: CanonicalId
    adapter_id: CanonicalId
    severity: DiagnosticSeverity
    code: str
    message: str
    source_native_id: str | None = None
    details: dict[str, JsonValue] = Field(default_factory=dict)


class CollectionFragment(TracecaseModel):
    fragment_id: CanonicalId
    adapter_id: CanonicalId
    sources: tuple[SourceDescriptor, ...] = ()
    components: tuple[Component, ...] = ()
    boundaries: tuple[Boundary, ...] = ()
    resources: tuple[Resource, ...] = ()
    nodes: tuple[ExecutionNode, ...] = ()
    relations: tuple[ExecutionRelation, ...] = ()
    contexts: tuple[ContextField, ...] = ()
    state_facts: tuple[StateFact, ...] = ()
    effects: tuple[Effect, ...] = ()
    observations: tuple[Observation, ...] = ()
    diagnostics: tuple[AdapterDiagnostic, ...] = ()
    extensions: dict[Namespace, JsonValue] = Field(default_factory=dict)


class CollectionResult(TracecaseModel):
    request: CollectionRequest
    fragments: tuple[CollectionFragment, ...]
    merged: CollectionFragment
    diagnostics: tuple[AdapterDiagnostic, ...]
    partial: bool
    adapter_status: dict[CanonicalId, str]
    attributes: dict[str, JsonValue] = Field(default_factory=dict)
