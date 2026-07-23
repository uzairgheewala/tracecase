from __future__ import annotations

import fnmatch
import hashlib
import hmac
import json
import re
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

from tracecase_bundle import canonical_json_bytes, digest_bytes
from tracecase_model import ExecutionCase, SensitivityLabel

from .models import (
    FieldInventory,
    InventoryItem,
    PolicyRule,
    PolicyViolation,
    RedactionAction,
    RedactionPolicy,
    RedactionReport,
    TransformationRecord,
)

_SENSITIVE_KEY_LABELS: tuple[tuple[re.Pattern[str], SensitivityLabel], ...] = (
    (re.compile(r"(?i)(^|[_.-])(authorization|cookie|password|passwd|secret|api[_-]?key|access[_-]?token|refresh[_-]?token)($|[_.-])"), SensitivityLabel.CREDENTIAL),
    (re.compile(r"(?i)(^|[_.-])(student|transcript|grade|course[_-]?history|advising[_-]?note)($|[_.-])"), SensitivityLabel.STUDENT_RECORD),
    (re.compile(r"(?i)(^|[_.-])(user[_-]?id|principal|email|phone)($|[_.-])"), SensitivityLabel.USER_IDENTIFIER),
    (re.compile(r"(?i)(^|[_.-])(tenant|institution[_-]?id)($|[_.-])"), SensitivityLabel.TENANT_IDENTIFIER),
    (re.compile(r"(?i)(^|[_.-])(query|sql)($|[_.-])"), SensitivityLabel.QUERY_TEXT),
    (re.compile(r"(?i)(^|[_.-])(note|comment|description|message|body|text)($|[_.-])"), SensitivityLabel.FREE_TEXT),
)

_STRUCTURAL_KEYS = {
    "node_id", "relation_id", "context_id", "fact_id", "effect_id", "observation_id",
    "component_id", "boundary_id", "resource_id", "source_id", "case_id", "system_id",
    "source_ref", "target_ref", "component_ref", "producer_node_ref", "observation_ref",
    "origin_node_ref", "observed_at_node_ref", "transaction_ref",
}
_FLEXIBLE_CONTAINERS = {"attributes", "extensions", "inputs", "outputs", "collection_scope", "entity_refs"}
_SENSITIVE_VALUE_KEYS = {"value", "attributes", "inputs", "outputs", "captured_payload", "logical_effect_key", "idempotency_key", "source_native_id", "principal_id", "tenant_id", "session_id", "entity_refs"}


class PolicyEngine:
    def __init__(self, policy: RedactionPolicy, *, token_key: bytes = b"tracecase-development-redaction-key") -> None:
        if not token_key:
            raise ValueError("token_key cannot be empty")
        self.policy = policy
        self.token_key = token_key
        self._token_cache: dict[str, str] = {}

    def inventory(self, case: ExecutionCase) -> FieldInventory:
        payload = case.model_dump(mode="json", exclude_none=False)
        items: list[InventoryItem] = []
        self._walk_inventory(payload, "$", (), items)
        return FieldInventory(
            inventory_id=f"inventory.{case.specification.case_id}.{self.policy.policy_id}",
            case_id=case.specification.case_id,
            policy_ref=self.policy.policy_id,
            items=tuple(items),
            by_label=dict(Counter(label.value for item in items for label in item.labels)),
            by_action=dict(Counter(item.proposed_action.value for item in items)),
        )

    def apply(self, case: ExecutionCase) -> tuple[ExecutionCase, RedactionReport]:
        original = case.model_dump(mode="json", exclude_none=False)
        transformed = deepcopy(original)
        records: list[TransformationRecord] = []
        violations: list[PolicyViolation] = []
        removed: list[str] = []
        transformed = self._transform(transformed, "$", (), None, records, violations, removed)
        transformed_case = ExecutionCase.model_validate(transformed)
        input_digest = digest_bytes(canonical_json_bytes(original))
        output_digest = digest_bytes(canonical_json_bytes(transformed))
        summary = Counter(record.action.value for record in records)
        report = RedactionReport(
            report_id=f"redaction.{case.specification.case_id}.{self.policy.policy_id}",
            case_id=case.specification.case_id,
            policy_ref=self.policy.policy_id,
            profile=self.policy.profile,
            generated_at=datetime.now(timezone.utc),
            transformations=tuple(records),
            violations=tuple(violations),
            removed_paths=tuple(removed),
            token_count=len(self._token_cache),
            input_digest=input_digest,
            output_digest=output_digest,
            valid_for_export=not any(item.severity == "error" for item in violations),
            summary=dict(summary),
        )
        return transformed_case, report

    def _walk_inventory(self, value: Any, path: str, inherited: tuple[SensitivityLabel, ...], output: list[InventoryItem], key: str | None = None) -> None:
        labels = self._labels(value, key, inherited)
        if isinstance(value, dict):
            declared = self._declared_labels(value)
            for child_key, child in value.items():
                child_labels = self._child_labels(child_key, key, labels, declared)
                self._walk_inventory(child, f"{path}.{child_key}", child_labels, output, child_key)
            return
        if isinstance(value, list):
            for index, child in enumerate(value):
                self._walk_inventory(child, f"{path}[{index}]", labels, output, key)
            return
        rule = self._match_rule(path, key, value, labels)
        action = rule.action if rule else self.policy.default_action
        output.append(InventoryItem(
            path=path,
            value_type=type(value).__name__,
            labels=labels,
            matched_rule_ref=rule.rule_id if rule else None,
            proposed_action=action,
            preview=self._preview(value),
            structural=bool(key in _STRUCTURAL_KEYS),
        ))

    def _transform(self, value: Any, path: str, inherited: tuple[SensitivityLabel, ...], parent_key: str | None, records: list[TransformationRecord], violations: list[PolicyViolation], removed: list[str]) -> Any:
        labels = self._labels(value, parent_key, inherited)
        if isinstance(value, dict):
            declared = self._declared_labels(value)
            result: dict[str, Any] = {}
            for key, child in value.items():
                child_path = f"{path}.{key}"
                child_labels = self._child_labels(key, parent_key, labels, declared)
                rule = self._match_rule(child_path, key, child, self._labels(child, key, child_labels))
                action = rule.action if rule else None
                if action is RedactionAction.REMOVE and parent_key in _FLEXIBLE_CONTAINERS:
                    self._record(records, child_path, child, action, rule, self._labels(child, key, child_labels), None, True)
                    removed.append(child_path)
                    continue
                result[key] = self._transform(child, child_path, child_labels, key, records, violations, removed)
            return result
        if isinstance(value, list):
            return [self._transform(child, f"{path}[{index}]", labels, parent_key, records, violations, removed) for index, child in enumerate(value)]
        rule = self._match_rule(path, parent_key, value, labels)
        action = rule.action if rule else self.policy.default_action
        if action is RedactionAction.RETAIN or value is None or parent_key in _STRUCTURAL_KEYS:
            return value
        if action is RedactionAction.REJECT:
            violations.append(PolicyViolation(
                violation_id=self._stable_id("violation", path), code="policy_reject", severity="error", path=path,
                message="Policy rejects this value from export.", rule_ref=rule.rule_id if rule else None, preview=self._preview(value),
            ))
            replacement = "[PROHIBITED]"
        elif action is RedactionAction.REMOVE:
            replacement = None if value is None else "[REDACTED]"
        elif action is RedactionAction.TOKENIZE:
            replacement = self._token(value, labels)
        elif action is RedactionAction.DIGEST:
            replacement = digest_bytes(canonical_json_bytes(value))
        elif action is RedactionAction.MASK:
            replacement = self._mask(value)
        elif action is RedactionAction.TRUNCATE:
            text = str(value)
            replacement = text[: (rule.max_length if rule else 48)] + ("…" if len(text) > (rule.max_length if rule else 48) else "")
        elif action is RedactionAction.SUMMARIZE:
            replacement = self._summarize(value)
        else:
            replacement = value
        self._record(records, path, value, action, rule, labels, replacement, False)
        return replacement

    @staticmethod
    def _child_labels(child_key: str, parent_key: str | None, inherited: tuple[SensitivityLabel, ...], declared: tuple[SensitivityLabel, ...]) -> tuple[SensitivityLabel, ...]:
        if child_key == "sensitivity":
            return ()
        if parent_key in _FLEXIBLE_CONTAINERS or child_key in _SENSITIVE_VALUE_KEYS:
            return tuple(sorted(set(inherited) | set(declared), key=lambda item: item.value))
        return inherited

    def _match_rule(self, path: str, key: str | None, value: Any, labels: tuple[SensitivityLabel, ...]) -> PolicyRule | None:
        normalized_path = re.sub(r"\[\d+\]", "[*]", path)
        for rule in sorted(self.policy.rules, key=lambda item: item.priority):
            if rule.path_glob != "*" and not fnmatch.fnmatch(normalized_path, rule.path_glob):
                continue
            if rule.labels and not set(rule.labels).intersection(labels):
                continue
            if rule.key_pattern and not re.search(rule.key_pattern, key or ""):
                continue
            if rule.value_pattern and not re.search(rule.value_pattern, str(value)):
                continue
            return rule
        return None

    def _labels(self, value: Any, key: str | None, inherited: tuple[SensitivityLabel, ...]) -> tuple[SensitivityLabel, ...]:
        labels = set(inherited)
        if key:
            for pattern, label in _SENSITIVE_KEY_LABELS:
                if pattern.search(key):
                    labels.add(label)
        if isinstance(value, str) and "@" in value and re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value):
            labels.add(SensitivityLabel.USER_IDENTIFIER)
        return tuple(sorted(labels, key=lambda item: item.value))

    @staticmethod
    def _declared_labels(value: dict[str, Any]) -> tuple[SensitivityLabel, ...]:
        raw = value.get("sensitivity")
        if not raw:
            return ()
        values = raw if isinstance(raw, list) else [raw]
        labels: list[SensitivityLabel] = []
        for item in values:
            try:
                labels.append(SensitivityLabel(item))
            except ValueError:
                continue
        return tuple(sorted(set(labels), key=lambda item: item.value))

    def _token(self, value: Any, labels: tuple[SensitivityLabel, ...]) -> str:
        canonical = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        cache_key = f"{','.join(label.value for label in labels)}:{canonical}"
        if cache_key not in self._token_cache:
            digest = hmac.new(self.token_key, cache_key.encode(), hashlib.sha256).hexdigest()[:14]
            prefix = labels[0].value.split("_")[0] if labels else "value"
            self._token_cache[cache_key] = f"{prefix}_{digest}"
        return self._token_cache[cache_key]

    @staticmethod
    def _mask(value: Any) -> str:
        text = str(value)
        if len(text) <= 4:
            return "*" * len(text)
        return f"{text[:2]}{'*' * min(len(text) - 4, 12)}{text[-2:]}"

    @staticmethod
    def _summarize(value: Any) -> str:
        text = str(value)
        return f"[redacted free text: {len(text)} chars, sha256:{hashlib.sha256(text.encode()).hexdigest()[:12]}]"

    @staticmethod
    def _preview(value: Any) -> str:
        if value is None:
            return "null"
        text = str(value).replace("\n", " ")
        return text[:64] + ("…" if len(text) > 64 else "")

    def _record(self, records: list[TransformationRecord], path: str, original: Any, action: RedactionAction, rule: PolicyRule | None, labels: tuple[SensitivityLabel, ...], replacement: Any, removed: bool) -> None:
        records.append(TransformationRecord(
            transformation_id=self._stable_id("transform", path), path=path, action=action,
            rule_ref=rule.rule_id if rule else None, labels=labels, original_type=type(original).__name__,
            original_digest=digest_bytes(canonical_json_bytes(original)), replacement_preview=None if removed else self._preview(replacement),
            removed=removed, referential_token=replacement if action is RedactionAction.TOKENIZE and isinstance(replacement, str) else None,
        ))

    @staticmethod
    def _stable_id(prefix: str, value: str) -> str:
        return f"{prefix}.{hashlib.sha256(value.encode()).hexdigest()[:20]}"
