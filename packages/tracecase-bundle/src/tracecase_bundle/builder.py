from __future__ import annotations

import shutil
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Iterable

from tracecase_model import ExecutionCase, build_core_schema_catalog

from .canonical import canonical_json_bytes, canonical_json_text, digest_bytes, digest_file
from .models import (
    AnalysisDescriptor,
    BundleLifecycle,
    BundleManifest,
    BundleProfile,
    CollectionDescriptor,
    ContentEntry,
    ContentIndex,
    IntegrityDescriptor,
    PrivacyDescriptor,
    ProducerDescriptor,
    ScenarioDescriptor,
)


@dataclass(frozen=True)
class BuildResult:
    bundle_path: Path
    manifest: BundleManifest
    content_index: ContentIndex


@dataclass(frozen=True)
class SupplementalArtifact:
    """Opaque, schema-versioned artifact written without coupling bundle code to producers."""

    path: str
    value: object
    media_type: str = "application/json"
    json_lines: bool = False
    required: bool = True


class BundleBuilder:
    """Build a deterministic directory-form Tracecase bundle."""

    PAYLOAD_ROOTS = (
        "specification",
        "provenance",
        "evidence",
        "model",
        "analysis",
        "comparison",
        "policy",
        "reports",
        "schemas",
        "synthetic",
        "collection",
        "registry",
    )
    RESERVED_PATHS = {
        "manifest.json",
        "specification/case.json",
        "specification/system_snapshot.json",
        "provenance/sources.json",
        "evidence/observations.jsonl",
        "evidence/state_facts.jsonl",
        "evidence/effects.jsonl",
        "model/nodes.jsonl",
        "model/relations.jsonl",
        "model/contexts.jsonl",
        "model/execution.json",
        "analysis/interpretations.json",
        "schemas/schema_catalog.json",
        "integrity/content_index.json",
        "integrity/checksums.json",
        "integrity/validation_report.json",
    }

    def __init__(self, output_path: Path, *, producer: ProducerDescriptor | None = None) -> None:
        self.output_path = output_path
        self.producer = producer or ProducerDescriptor(name="tracecase", version="0.2.0")
        self._frozen = False

    def build(
        self,
        case: ExecutionCase,
        *,
        overwrite: bool = False,
        supplements: Iterable[SupplementalArtifact] = (),
        profiles: tuple[BundleProfile, ...] | None = None,
        scenario: ScenarioDescriptor | None = None,
        collection: CollectionDescriptor | None = None,
        analysis_status: str = "not_started",
    ) -> BuildResult:
        if self._frozen:
            raise RuntimeError("builder has already frozen a bundle")
        if self.output_path.exists():
            if not overwrite:
                raise FileExistsError(self.output_path)
            if self.output_path.is_dir():
                shutil.rmtree(self.output_path)
            else:
                self.output_path.unlink()
        self.output_path.mkdir(parents=True)

        self._write_case(case)
        self._write_schema_catalog()
        self._write_placeholder_reports(analysis_status)
        for supplement in supplements:
            self._write_supplement(supplement)

        content_index = self._build_content_index()
        self._write_json("integrity/content_index.json", content_index)
        self._write_json(
            "integrity/checksums.json",
            {entry.path: entry.digest for entry in content_index.entries},
        )

        evidence_entries = [
            entry
            for entry in content_index.entries
            if entry.layer in {"specification", "provenance", "evidence", "model", "synthetic", "collection"}
        ]
        evidence_digest = self._digest_index(evidence_entries)
        bundle_digest = self._digest_index(list(content_index.entries))
        now = datetime.now(timezone.utc)
        manifest = BundleManifest(
            bundle_id=f"bundle.{case.specification.case_id}",
            case_id=case.specification.case_id,
            case_category=case.specification.category.value,
            profiles=profiles or (BundleProfile.EVIDENCE, BundleProfile.REPRODUCIBLE),
            lifecycle=BundleLifecycle.FROZEN,
            created_at=case.specification.created_at,
            frozen_at=now,
            producer=self.producer,
            roots=case.specification.roots,
            baselines=case.specification.baseline_case_refs,
            privacy=PrivacyDescriptor(classification="internal"),
            analysis=AnalysisDescriptor(
                status=analysis_status,
                analysis_runs_ref=("analysis/graph_assembly_report.json" if analysis_status != "not_started" else None),
            ),
            scenario=scenario,
            collection=collection or CollectionDescriptor(),
            integrity=IntegrityDescriptor(
                evidence_digest=evidence_digest,
                bundle_digest=bundle_digest,
            ),
        )
        self._write_json("manifest.json", manifest)
        self._write_json(
            "integrity/validation_report.json",
            {
                "valid": True,
                "checked_at": now,
                "issues": [],
            },
        )
        self._frozen = True
        return BuildResult(self.output_path, manifest, content_index)

    def pack(self, archive_path: Path, *, overwrite: bool = False) -> Path:
        if not self._frozen:
            raise RuntimeError("build and freeze the bundle before packing")
        if archive_path.exists() and not overwrite:
            raise FileExistsError(archive_path)
        archive_path.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(self.output_path.rglob("*")):
                if path.is_file():
                    archive.write(path, path.relative_to(self.output_path).as_posix())
        return archive_path

    def _write_case(self, case: ExecutionCase) -> None:
        self._write_json("specification/case.json", case.specification)
        self._write_json("specification/system_snapshot.json", case.system)
        self._write_json("provenance/sources.json", list(case.evidence.sources))
        self._write_jsonl("evidence/observations.jsonl", case.evidence.execution.observations)
        self._write_jsonl("evidence/state_facts.jsonl", case.evidence.execution.state_facts)
        self._write_jsonl("evidence/effects.jsonl", case.evidence.execution.effects)
        self._write_jsonl("model/nodes.jsonl", case.evidence.execution.nodes)
        self._write_jsonl("model/relations.jsonl", case.evidence.execution.relations)
        self._write_jsonl("model/contexts.jsonl", case.evidence.execution.contexts)
        self._write_json(
            "model/execution.json",
            {
                "execution_id": case.evidence.execution.execution_id,
                "evidence_classification": case.evidence.execution.evidence_classification,
                "extensions": case.evidence.execution.extensions,
            },
        )
        self._write_json("analysis/interpretations.json", case.interpretations)

    def _write_schema_catalog(self) -> None:
        self._write_json("schemas/schema_catalog.json", build_core_schema_catalog())

    def _write_placeholder_reports(self, analysis_status: str) -> None:
        self._write_json(
            "reports/machine_summary.json",
            {
                "status": analysis_status,
                "message": (
                    "Canonical evidence and derived execution graph are available."
                    if analysis_status != "not_started"
                    else "Bundle contains canonical evidence but no analyzer outputs."
                ),
            },
        )

    def _write_supplement(self, supplement: SupplementalArtifact) -> None:
        path = PurePosixPath(supplement.path)
        if path.is_absolute() or ".." in path.parts or len(path.parts) < 2:
            raise ValueError(f"unsafe supplemental path: {supplement.path}")
        if path.parts[0] not in self.PAYLOAD_ROOTS:
            raise ValueError(f"unsupported supplemental layer: {path.parts[0]}")
        normalized = path.as_posix()
        if normalized in self.RESERVED_PATHS:
            raise ValueError(f"supplement cannot overwrite reserved path: {normalized}")
        if supplement.json_lines:
            if not isinstance(supplement.value, Iterable) or isinstance(supplement.value, (str, bytes, dict)):
                raise TypeError("JSONL supplement value must be a non-string iterable")
            self._write_jsonl(normalized, supplement.value)
        else:
            self._write_json(normalized, supplement.value)

    def _write_json(self, relative_path: str, value: object) -> None:
        path = self.output_path / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(canonical_json_bytes(value))

    def _write_jsonl(self, relative_path: str, values: Iterable[object]) -> None:
        path = self.output_path / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="\n") as handle:
            for value in values:
                handle.write(canonical_json_text(value))

    def _build_content_index(self) -> ContentIndex:
        entries: list[ContentEntry] = []
        for root_name in self.PAYLOAD_ROOTS:
            root_path = self.output_path / root_name
            if not root_path.exists():
                continue
            for path in sorted(root_path.rglob("*")):
                if not path.is_file():
                    continue
                relative = path.relative_to(self.output_path).as_posix()
                entries.append(
                    ContentEntry(
                        path=relative,
                        media_type=self._media_type(path),
                        size_bytes=path.stat().st_size,
                        digest=digest_file(path),
                        layer=root_name,
                    )
                )
        return ContentIndex(entries=tuple(entries))

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

    @staticmethod
    def _media_type(path: Path) -> str:
        if path.suffix == ".jsonl":
            return "application/x-ndjson"
        if path.suffix == ".json":
            return "application/json"
        if path.suffix == ".html":
            return "text/html"
        return "application/octet-stream"

    @staticmethod
    def unpack(archive_path: Path, destination: Path, *, overwrite: bool = False) -> Path:
        if destination.exists():
            if not overwrite:
                raise FileExistsError(destination)
            shutil.rmtree(destination)
        destination.mkdir(parents=True)
        with zipfile.ZipFile(archive_path) as archive:
            for member in archive.infolist():
                target = (destination / member.filename).resolve()
                if destination.resolve() not in target.parents and target != destination.resolve():
                    raise ValueError(f"unsafe archive path: {member.filename}")
            archive.extractall(destination)
        return destination

    @staticmethod
    def read_archive_temporarily(archive_path: Path) -> tempfile.TemporaryDirectory[str]:
        temporary = tempfile.TemporaryDirectory(prefix="tracecase-")
        BundleBuilder.unpack(archive_path, Path(temporary.name))
        return temporary
