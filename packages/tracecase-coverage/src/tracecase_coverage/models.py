from __future__ import annotations

from enum import StrEnum
from pydantic import Field, JsonValue
from tracecase_model import TracecaseModel
from tracecase_model.types import CanonicalId

class CoverageDimension(StrEnum):
    FAMILY = "family"
    UNIVERSE_AXIS = "universe_axis"
    TOPOLOGY = "topology"
    FAULT_OPERATOR = "fault_operator"
    INVARIANT = "invariant"
    OBSERVABILITY = "observability"
    INTERACTION = "interaction"
    OUTCOME = "outcome"
    REALIZATION = "realization"

class CoverageStatus(StrEnum):
    COVERED = "covered"
    UNCOVERED = "uncovered"
    INVALID = "invalid"
    UNSUPPORTED = "unsupported"

class CoveragePoint(TracecaseModel):
    point_id: CanonicalId
    dimension: CoverageDimension
    key: str
    status: CoverageStatus
    family_ref: CanonicalId | None = None
    witness_refs: tuple[str, ...] = ()
    rationale: str | None = None
    attributes: dict[str, JsonValue] = Field(default_factory=dict)

class CoverageRecommendation(TracecaseModel):
    recommendation_id: CanonicalId
    family_ref: CanonicalId
    priority: int = Field(ge=1)
    uncovered_point_refs: tuple[CanonicalId, ...]
    suggested_fault_ref: CanonicalId | None = None
    suggested_observability_profile: str | None = None
    rationale: str

class CoverageLedger(TracecaseModel):
    ledger_id: CanonicalId
    registry_version: str
    points: tuple[CoveragePoint, ...]
    recommendations: tuple[CoverageRecommendation, ...] = ()
    summary: dict[str, int]
    attributes: dict[str, JsonValue] = Field(default_factory=dict)

class MutationTrial(TracecaseModel):
    trial_id: CanonicalId
    mutation_ref: str
    target_ref: str
    detected: bool
    expected_changes: tuple[str, ...] = ()
    actual_changes: tuple[str, ...] = ()
    unexpected_changes: tuple[str, ...] = ()

class MutationAdequacyReport(TracecaseModel):
    report_id: CanonicalId
    trials: tuple[MutationTrial, ...]
    score: float = Field(ge=0.0, le=1.0)
    detected: int = Field(ge=0)
    survived: int = Field(ge=0)

class MinimizationStep(TracecaseModel):
    step_id: CanonicalId
    dimension: str
    removed: tuple[str, ...]
    preserved: bool
    candidate_digest: str

class MinimizationReport(TracecaseModel):
    report_id: CanonicalId
    original_ref: str
    minimized_ref: str
    target_ref: str
    steps: tuple[MinimizationStep, ...]
    original_size: int = Field(ge=0)
    minimized_size: int = Field(ge=0)
    reduction_ratio: float = Field(ge=0.0, le=1.0)
    attributes: dict[str, JsonValue] = Field(default_factory=dict)
