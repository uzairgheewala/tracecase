from __future__ import annotations
import json
from pathlib import Path
from tracecase_bundle import BundleReader
from .models import *

class CompatibilityEngine:
    SUPPORTED_FORMATS=("1.0.0",)
    LEGACY_MIGRATIONS={"0.9.0":"1.0.0"}

    def assess(self, reader: BundleReader) -> CompatibilityAssessment:
        version=reader.manifest.format_version; issues=[]; actions=[]
        if version in self.SUPPORTED_FORMATS: status=CompatibilityStatus.COMPATIBLE
        elif version in self.LEGACY_MIGRATIONS:
            status=CompatibilityStatus.MIGRATABLE; actions.append(f"Migrate bundle format {version} to {self.LEGACY_MIGRATIONS[version]}.")
        else:
            status=CompatibilityStatus.UNKNOWN; issues.append(CompatibilityIssue(code="unsupported_format",severity="error",message=f"Format {version} is not declared compatible."))
        namespaces=self._extension_namespaces(reader)
        if namespaces: actions.append("Preserve unknown namespaced extensions during migration and reserialization.")
        verification=reader.verify()
        if not verification.valid:
            status=CompatibilityStatus.INCOMPATIBLE
            issues.append(CompatibilityIssue(code="integrity_failure",severity="error",message="Bundle integrity verification failed."))
        return CompatibilityAssessment(
            assessment_id=f"compat.{reader.manifest.bundle_id}", bundle_ref=reader.manifest.bundle_id,
            status=status, format_version=version, supported_format_versions=self.SUPPORTED_FORMATS,
            issues=tuple(issues), extension_namespaces=tuple(sorted(namespaces)), recommended_actions=tuple(actions),
        )

    def plan(self, source_version: str, target_version: str="1.0.0") -> MigrationPlan:
        if source_version==target_version:
            return MigrationPlan(plan_id=f"migration.{source_version}.{target_version}",source_version=source_version,target_version=target_version,steps=(),executable=True)
        if self.LEGACY_MIGRATIONS.get(source_version)==target_version:
            step=MigrationStep(step_id=f"migration-step.{source_version}.{target_version}",from_version=source_version,to_version=target_version,description="Normalize legacy manifest defaults and declare the 1.0 bundle contract.")
            return MigrationPlan(plan_id=f"migration.{source_version}.{target_version}",source_version=source_version,target_version=target_version,steps=(step,),executable=True)
        return MigrationPlan(plan_id=f"migration.{source_version}.{target_version}",source_version=source_version,target_version=target_version,steps=(),executable=False,limitations=("No registered migration path.",))

    @staticmethod
    def migrate_manifest(payload: dict, target_version: str="1.0.0") -> dict:
        source=str(payload.get("format_version","0.9.0"))
        if source==target_version: return dict(payload)
        if source!="0.9.0" or target_version!="1.0.0": raise ValueError(f"unsupported migration {source} -> {target_version}")
        value=dict(payload); value["format"]="tracecase.bundle"; value["format_version"]="1.0.0"
        value.setdefault("collection", {"status":"not_collected","request_ref":None,"result_ref":None})
        value.setdefault("scenario", None); value.setdefault("baselines", [])
        return value

    @staticmethod
    def _extension_namespaces(reader: BundleReader) -> set[str]:
        case=reader.load_case(); result=set(case.extensions)
        result.update(case.system.extensions); result.update(case.evidence.execution.extensions)
        for node in case.evidence.execution.nodes: result.update(node.extensions)
        return result

class BundleHealthScanner:
    def scan(self, reader: BundleReader) -> BundleHealthReport:
        verification=reader.verify(); malformed=[]; counts={}
        for entry in reader.content_index.entries:
            if entry.media_type!="application/x-ndjson": continue
            count=0
            try:
                for _ in reader.read_jsonl(entry.path): count += 1
            except ValueError: malformed.append(entry.path)
            counts[entry.path]=count
        recommendations=[]
        if verification.missing_paths: recommendations.append("Recover missing files from the source bundle or recollect evidence.")
        if verification.mismatched_paths: recommendations.append("Do not trust mutated content; restore from a verified revision.")
        if verification.unexpected_paths: recommendations.append("Classify and index unexpected files before freezing a new revision.")
        if malformed: recommendations.append("Repair malformed JSONL only in a new evidence revision.")
        return BundleHealthReport(
            report_id=f"health.{reader.manifest.bundle_id}", bundle_ref=reader.manifest.bundle_id,
            valid=verification.valid and not malformed,
            missing_paths=verification.missing_paths,mismatched_paths=verification.mismatched_paths,
            unexpected_paths=verification.unexpected_paths,malformed_jsonl=tuple(malformed),record_counts=counts,
            recoverable=not verification.mismatched_paths and not malformed,
            recommendations=tuple(recommendations),
        )
