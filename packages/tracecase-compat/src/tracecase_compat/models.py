from __future__ import annotations
from enum import StrEnum
from pydantic import Field, JsonValue
from tracecase_model import TracecaseModel

class CompatibilityStatus(StrEnum):
    COMPATIBLE="compatible"; MIGRATABLE="migratable"; INCOMPATIBLE="incompatible"; UNKNOWN="unknown"

class CompatibilityIssue(TracecaseModel):
    code: str; severity: str; message: str; path: str | None = None
    attributes: dict[str, JsonValue] = Field(default_factory=dict)

class CompatibilityAssessment(TracecaseModel):
    assessment_id: str; bundle_ref: str; status: CompatibilityStatus
    format_version: str; supported_format_versions: tuple[str,...]
    issues: tuple[CompatibilityIssue,...] = (); extension_namespaces: tuple[str,...] = ()
    recommended_actions: tuple[str,...] = ()

class MigrationStep(TracecaseModel):
    step_id: str; from_version: str; to_version: str; description: str; lossless: bool = True

class MigrationPlan(TracecaseModel):
    plan_id: str; source_version: str; target_version: str; steps: tuple[MigrationStep,...]
    executable: bool; limitations: tuple[str,...] = ()

class BundleHealthReport(TracecaseModel):
    report_id: str; bundle_ref: str; valid: bool
    missing_paths: tuple[str,...]=(); mismatched_paths: tuple[str,...]=(); unexpected_paths: tuple[str,...]=()
    malformed_jsonl: tuple[str,...]=(); record_counts: dict[str,int]=Field(default_factory=dict)
    recoverable: bool=False; recommendations: tuple[str,...]=()

class QueryIndexSummary(TracecaseModel):
    index_id: str; node_count: int; component_count: int; operation_count: int
    identity_value_count: int; effect_key_count: int

class GraphNeighborhood(TracecaseModel):
    center_ref: str; depth: int; node_refs: tuple[str,...]; relation_refs: tuple[str,...]
