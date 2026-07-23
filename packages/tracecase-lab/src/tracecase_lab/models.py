from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import Field, JsonValue, field_validator

from tracecase_analyzers import AnalysisReport
from tracecase_compare import SemanticComparison
from tracecase_graph import AssembledExecutionGraph, TimelineModel
from tracecase_model import ExecutionCase, TracecaseModel


class LabMode(StrEnum):
    IN_PROCESS = "in_process"
    DISTRIBUTED = "distributed"


class LabRunStatus(StrEnum):
    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class LabBinding(TracecaseModel):
    binding_id: str
    family_ref: str
    title: str
    description: str
    supported_faults: tuple[str, ...]
    topology_roles: tuple[str, ...]
    invariant_refs: tuple[str, ...]
    runtime_modes: tuple[LabMode, ...] = (LabMode.IN_PROCESS,)


class LabRunRequest(TracecaseModel):
    binding_ref: str = "lab.transcript-import.v1"
    mode: LabMode = LabMode.IN_PROCESS
    seed: int = Field(default=1, ge=0)
    fault_operator_ref: str | None = None
    fault_target: str | None = None
    observability_fault_ref: str | None = None
    tenant_id: str = "institution-alpha"
    principal_id: str = "student-1001"
    transcript_courses: tuple[str, ...] = ("DSC100", "DSC180A", "DSC180B")
    include_sensitive_payload: bool = False
    attributes: dict[str, JsonValue] = Field(default_factory=dict)


class LabEvent(TracecaseModel):
    event_id: str
    timestamp: datetime
    component: str
    operation: str
    node_kind: str
    status: str
    parent_event_id: str | None = None
    identities: dict[str, JsonValue]
    attributes: dict[str, JsonValue] = Field(default_factory=dict)
    sensitive_attributes: dict[str, JsonValue] = Field(default_factory=dict)

    @field_validator("timestamp")
    @classmethod
    def aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("timestamp must be timezone-aware")
        return value


class LabRunReceipt(TracecaseModel):
    run_id: str
    binding_ref: str
    mode: LabMode
    status: LabRunStatus
    started_at: datetime
    completed_at: datetime
    fault_operator_ref: str | None = None
    observability_fault_ref: str | None = None
    event_count: int
    case_id: str
    attributes: dict[str, JsonValue] = Field(default_factory=dict)

    @field_validator("started_at", "completed_at")
    @classmethod
    def aware_times(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("lab timestamps must be timezone-aware")
        return value


class LabRunResult(TracecaseModel):
    receipt: LabRunReceipt
    case: ExecutionCase
    graph: AssembledExecutionGraph
    timeline: TimelineModel
    analysis: AnalysisReport
    events: tuple[LabEvent, ...]


class LabComparisonResult(TracecaseModel):
    baseline: LabRunResult
    candidate: LabRunResult
    comparison: SemanticComparison
