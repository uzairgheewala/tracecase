from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import Field, JsonValue, field_validator

from tracecase_model import SensitivityLabel, TracecaseModel


class RedactionAction(StrEnum):
    RETAIN = "retain"
    TOKENIZE = "tokenize"
    DIGEST = "digest"
    MASK = "mask"
    TRUNCATE = "truncate"
    REMOVE = "remove"
    SUMMARIZE = "summarize"
    REJECT = "reject"


class ExportProfile(StrEnum):
    INTERNAL = "internal"
    SHAREABLE = "shareable"
    PUBLIC = "public"


class RuleMatchKind(StrEnum):
    PATH = "path"
    LABEL = "label"
    KEY = "key"
    VALUE = "value"


class PolicyRule(TracecaseModel):
    rule_id: str
    action: RedactionAction
    path_glob: str = "*"
    labels: tuple[SensitivityLabel, ...] = ()
    key_pattern: str | None = None
    value_pattern: str | None = None
    priority: int = 100
    replacement: str | None = None
    max_length: int = Field(default=48, ge=1, le=4096)
    description: str = ""


class RedactionPolicy(TracecaseModel):
    policy_id: str
    version: str = "1.0.0"
    title: str
    profile: ExportProfile
    default_action: RedactionAction = RedactionAction.RETAIN
    rules: tuple[PolicyRule, ...]
    prohibited_patterns: tuple[str, ...] = ()
    preserve_referential_integrity: bool = True
    stable_token_scope: str = "bundle"
    attributes: dict[str, JsonValue] = Field(default_factory=dict)


class InventoryItem(TracecaseModel):
    path: str
    value_type: str
    labels: tuple[SensitivityLabel, ...]
    matched_rule_ref: str | None = None
    proposed_action: RedactionAction
    preview: str
    structural: bool = False


class FieldInventory(TracecaseModel):
    inventory_id: str
    case_id: str
    policy_ref: str
    items: tuple[InventoryItem, ...]
    by_label: dict[str, int]
    by_action: dict[str, int]


class TransformationRecord(TracecaseModel):
    transformation_id: str
    path: str
    action: RedactionAction
    rule_ref: str | None = None
    labels: tuple[SensitivityLabel, ...] = ()
    original_type: str
    original_digest: str
    replacement_preview: str | None = None
    removed: bool = False
    referential_token: str | None = None


class PolicyViolation(TracecaseModel):
    violation_id: str
    code: str
    severity: str
    path: str
    message: str
    rule_ref: str | None = None
    preview: str | None = None


class RedactionReport(TracecaseModel):
    report_id: str
    case_id: str
    policy_ref: str
    profile: ExportProfile
    generated_at: datetime
    transformations: tuple[TransformationRecord, ...]
    violations: tuple[PolicyViolation, ...]
    removed_paths: tuple[str, ...]
    token_count: int
    input_digest: str
    output_digest: str
    valid_for_export: bool
    summary: dict[str, int]

    @field_validator("generated_at")
    @classmethod
    def aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("generated_at must be timezone-aware")
        return value


class ExportValidationReport(TracecaseModel):
    report_id: str
    case_id: str
    policy_ref: str
    profile: ExportProfile
    valid: bool
    checked_at: datetime
    violations: tuple[PolicyViolation, ...]
    scanned_values: int
    prohibited_matches: int
    integrity_valid: bool | None = None
    omitted_artifacts: tuple[str, ...] = ()

    @field_validator("checked_at")
    @classmethod
    def checked_at_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("checked_at must be timezone-aware")
        return value


class ExportResult(TracecaseModel):
    source_case_id: str
    exported_case_id: str
    bundle_path: str
    archive_path: str | None = None
    policy_ref: str
    redaction_report: RedactionReport
    validation_report: ExportValidationReport
