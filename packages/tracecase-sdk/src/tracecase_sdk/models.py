from __future__ import annotations
from datetime import datetime
from enum import StrEnum
from pydantic import Field, JsonValue, field_validator
from tracecase_model import SensitivityLabel, TracecaseModel

class SDKEventKind(StrEnum):
    OPERATION_START="operation_start"; OPERATION_END="operation_end"; DOMAIN_EVENT="domain_event"; EFFECT="effect"; CONTEXT="context"; ERROR="error"

class SDKContext(TracecaseModel):
    trace_id: str | None=None; workflow_id: str | None=None; logical_operation_id: str | None=None
    task_id: str | None=None; task_attempt: int | None=None; tenant_id: str | None=None; principal_id: str | None=None
    idempotency_key: str | None=None; attributes: dict[str,JsonValue]=Field(default_factory=dict)

class SDKEvent(TracecaseModel):
    event_id: str; kind: SDKEventKind; timestamp: datetime; component: str; operation: str
    context: SDKContext=Field(default_factory=SDKContext); parent_event_id: str | None=None
    attributes: dict[str,JsonValue]=Field(default_factory=dict); sensitivity: set[SensitivityLabel]=Field(default_factory=set)
    @field_validator("timestamp")
    @classmethod
    def aware(cls,value):
        if value.tzinfo is None: raise ValueError("SDK event timestamps must be timezone-aware")
        return value

class EffectRecord(TracecaseModel):
    logical_effect_key: str; operation: str; target: str | None=None; durability: str="attempted"
    idempotency_key: str | None=None; attributes: dict[str,JsonValue]=Field(default_factory=dict)
