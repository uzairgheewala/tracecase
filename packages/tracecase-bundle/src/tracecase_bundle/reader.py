from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator, TypeVar

from pydantic import TypeAdapter

from tracecase_model import (
    CaseEvidence,
    CaseInterpretations,
    CaseSpecification,
    ContextField,
    Effect,
    ExecutionCase,
    ExecutionModel,
    ExecutionNode,
    ExecutionRelation,
    Observation,
    SourceDescriptor,
    StateFact,
    SystemModel,
)

from .builder import BundleBuilder
from .canonical import canonical_json_bytes, digest_bytes, digest_file
from .models import BundleManifest, ContentEntry, ContentIndex, ValidationIssue, ValidationReport

T = TypeVar("T")


@dataclass(frozen=True)
class VerificationResult:
    valid: bool
    missing_paths: tuple[str, ...]
    mismatched_paths: tuple[str, ...]
    unexpected_paths: tuple[str, ...]
    manifest: BundleManifest


class BundleReader:
    def __init__(self, bundle_path: Path) -> None:
        self.bundle_path = bundle_path
        if not bundle_path.is_dir():
            raise ValueError("BundleReader expects an unpacked directory bundle")
        self.manifest = BundleManifest.model_validate(self.read_json("manifest.json"))
        self.content_index = ContentIndex.model_validate(
            self.read_json(self.manifest.content_index_ref)
        )

    @classmethod
    def open(cls, path: Path) -> tuple["BundleReader", object | None]:
        if path.is_dir():
            return cls(path), None
        temporary = BundleBuilder.read_archive_temporarily(path)
        return cls(Path(temporary.name)), temporary

    def has_artifact(self, relative_path: str) -> bool:
        return (self.bundle_path / relative_path).is_file()

    def read_optional_json(self, relative_path: str) -> Any | None:
        if not self.has_artifact(relative_path):
            return None
        return self.read_json(relative_path)

    def read_json(self, relative_path: str) -> Any:
        path = self.bundle_path / relative_path
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def read_jsonl(self, relative_path: str) -> Iterator[Any]:
        path = self.bundle_path / relative_path
        if not path.exists():
            return
        with path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                if line.strip():
                    try:
                        yield json.loads(line)
                    except json.JSONDecodeError as exc:
                        raise ValueError(f"invalid JSONL at {relative_path}:{line_number}") from exc

    def load_case(self) -> ExecutionCase:
        specification = CaseSpecification.model_validate(self.read_json(self.manifest.case_ref))
        system = SystemModel.model_validate(self.read_json("specification/system_snapshot.json"))
        sources = tuple(
            TypeAdapter(list[SourceDescriptor]).validate_python(self.read_json("provenance/sources.json"))
        )
        nodes = tuple(ExecutionNode.model_validate(value) for value in self.read_jsonl("model/nodes.jsonl"))
        relations = tuple(
            ExecutionRelation.model_validate(value) for value in self.read_jsonl("model/relations.jsonl")
        )
        contexts = tuple(ContextField.model_validate(value) for value in self.read_jsonl("model/contexts.jsonl"))
        observations = tuple(
            Observation.model_validate(value) for value in self.read_jsonl("evidence/observations.jsonl")
        )
        state_facts = tuple(
            StateFact.model_validate(value) for value in self.read_jsonl("evidence/state_facts.jsonl")
        )
        effects = tuple(Effect.model_validate(value) for value in self.read_jsonl("evidence/effects.jsonl"))
        execution_header = self.read_json("model/execution.json")
        execution = ExecutionModel(
            execution_id=execution_header["execution_id"],
            nodes=nodes,
            relations=relations,
            contexts=contexts,
            state_facts=state_facts,
            effects=effects,
            observations=observations,
            evidence_classification=execution_header["evidence_classification"],
            extensions=execution_header.get("extensions", {}),
        )
        interpretations = CaseInterpretations.model_validate(
            self.read_json("analysis/interpretations.json")
        )
        return ExecutionCase(
            specification=specification,
            system=system,
            evidence=CaseEvidence(sources=sources, execution=execution),
            interpretations=interpretations,
            lifecycle=self.manifest.lifecycle.value,
        )

    def verify(self, *, report_unexpected: bool = True) -> VerificationResult:
        missing: list[str] = []
        mismatched: list[str] = []
        indexed_paths = {entry.path for entry in self.content_index.entries}
        for entry in self.content_index.entries:
            path = self.bundle_path / entry.path
            if not path.exists():
                missing.append(entry.path)
            elif digest_file(path) != entry.digest:
                mismatched.append(entry.path)

        unexpected: list[str] = []
        if report_unexpected:
            ignored = {
                "manifest.json",
                self.manifest.content_index_ref,
                self.manifest.checksums_ref,
                "integrity/validation_report.json",
            }
            for path in self.bundle_path.rglob("*"):
                if not path.is_file():
                    continue
                relative = path.relative_to(self.bundle_path).as_posix()
                if relative not in indexed_paths and relative not in ignored:
                    unexpected.append(relative)

        current_evidence = self._digest_index(
            [
                entry
                for entry in self.content_index.entries
                if entry.layer in {"specification", "provenance", "evidence", "model", "synthetic", "collection"}
            ]
        )
        current_bundle = self._digest_index(list(self.content_index.entries))
        if current_evidence != self.manifest.integrity.evidence_digest:
            mismatched.append("<evidence-digest>")
        if current_bundle != self.manifest.integrity.bundle_digest:
            mismatched.append("<bundle-digest>")

        return VerificationResult(
            valid=not missing and not mismatched and not unexpected,
            missing_paths=tuple(sorted(missing)),
            mismatched_paths=tuple(sorted(set(mismatched))),
            unexpected_paths=tuple(sorted(unexpected)),
            manifest=self.manifest,
        )

    def validation_report(self) -> ValidationReport:
        from datetime import datetime, timezone

        issues: list[ValidationIssue] = []
        try:
            self.load_case()
        except Exception as exc:
            issues.append(
                ValidationIssue(
                    severity="error",
                    code="case_model_invalid",
                    message=str(exc),
                )
            )
        verification = self.verify()
        for path in verification.missing_paths:
            issues.append(ValidationIssue(severity="error", code="missing_file", message="Indexed file is missing", path=path))
        for path in verification.mismatched_paths:
            issues.append(ValidationIssue(severity="error", code="digest_mismatch", message="Digest does not match", path=path))
        for path in verification.unexpected_paths:
            issues.append(ValidationIssue(severity="warning", code="unexpected_file", message="File is not indexed", path=path))
        return ValidationReport(valid=not any(issue.severity == "error" for issue in issues), checked_at=datetime.now(timezone.utc), issues=tuple(issues))

    @staticmethod
    def _digest_index(entries: list[ContentEntry]) -> str:
        payload = [
            {
                "path": entry.path,
                "digest": entry.digest,
                "size_bytes": entry.size_bytes,
                "layer": entry.layer,
            }
            for entry in sorted(entries, key=lambda item: item.path)
        ]
        return digest_bytes(canonical_json_bytes(payload))
