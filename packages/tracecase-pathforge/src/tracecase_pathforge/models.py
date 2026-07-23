from __future__ import annotations
from enum import StrEnum
from pydantic import Field, JsonValue
from tracecase_model import TracecaseModel

class PathforgeWorkflowKind(StrEnum):
    TRANSCRIPT_IMPORT="transcript_import"; REQUIREMENT_AUDIT="requirement_audit"; INTEGRATION_RECONCILIATION="integration_reconciliation"; PLAN_GENERATION="plan_generation"

class PathforgeRunContext(TracecaseModel):
    engagement_id: str; institution_id: str; workflow_id: str; run_id: str; workflow_kind: PathforgeWorkflowKind
    catalog_version: str | None=None; student_token: str | None=None; attributes: dict[str,JsonValue]=Field(default_factory=dict)

class PathforgeDomainEvent(TracecaseModel):
    event_id: str; event_type: str; stage: str; component: str; operation: str; context: PathforgeRunContext
    parent_event_id: str | None=None; status: str="ok"; attributes: dict[str,JsonValue]=Field(default_factory=dict)

class PathforgeBinding(TracecaseModel):
    binding_id: str; workflow_kind: PathforgeWorkflowKind; title: str; extension_namespace: str="pathforge.academic"
    generic_invariants: tuple[str,...]; domain_event_types: tuple[str,...]

class PathforgeRunResult(TracecaseModel):
    binding: PathforgeBinding; case_id: str; graph_id: str; invariant_summary: dict[str,int]; finding_count: int
    deep_link: str; attributes: dict[str,JsonValue]=Field(default_factory=dict)
