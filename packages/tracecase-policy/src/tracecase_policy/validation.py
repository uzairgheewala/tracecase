from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any

from tracecase_bundle import canonical_json_bytes
from tracecase_model import ExecutionCase

from .models import ExportValidationReport, PolicyViolation, RedactionPolicy


class ExportValidator:
    def validate_case(self, case: ExecutionCase, policy: RedactionPolicy, *, omitted_artifacts: tuple[str, ...] = ()) -> ExportValidationReport:
        payload = case.model_dump(mode="json", exclude_none=False)
        violations: list[PolicyViolation] = []
        scanned = 0
        matches = 0
        patterns = [(pattern, re.compile(pattern)) for pattern in policy.prohibited_patterns]
        for path, value in self._scalars(payload):
            scanned += 1
            text = str(value)
            for raw, pattern in patterns:
                if pattern.search(text):
                    matches += 1
                    violations.append(PolicyViolation(
                        violation_id=f"validation.{len(violations)+1}", code="prohibited_pattern", severity="error", path=path,
                        message=f"Value matches prohibited export pattern: {raw}", preview=text[:64],
                    ))
        return ExportValidationReport(
            report_id=f"export-validation.{case.specification.case_id}.{policy.policy_id}", case_id=case.specification.case_id,
            policy_ref=policy.policy_id, profile=policy.profile, valid=not violations, checked_at=datetime.now(timezone.utc),
            violations=tuple(violations), scanned_values=scanned, prohibited_matches=matches, omitted_artifacts=omitted_artifacts,
        )

    def validate_serialized(self, value: Any, policy: RedactionPolicy) -> tuple[PolicyViolation, ...]:
        text = canonical_json_bytes(value).decode("utf-8", errors="replace")
        output: list[PolicyViolation] = []
        for pattern in policy.prohibited_patterns:
            match = re.search(pattern, text)
            if match:
                output.append(PolicyViolation(
                    violation_id=f"serialized.{len(output)+1}", code="serialized_prohibited_pattern", severity="error", path="$",
                    message=f"Serialized payload matches prohibited pattern: {pattern}", preview=match.group(0)[:64],
                ))
        return tuple(output)

    def _scalars(self, value: Any, path: str = "$"):
        if isinstance(value, dict):
            for key, child in value.items():
                yield from self._scalars(child, f"{path}.{key}")
        elif isinstance(value, list):
            for index, child in enumerate(value):
                yield from self._scalars(child, f"{path}[{index}]")
        elif value is not None:
            yield path, value
