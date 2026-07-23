from __future__ import annotations

from pathlib import Path

from tracecase_analyzers import AnalyzerEngine
from tracecase_bundle import BundleBuilder, BundleProfile, BundleReader, PrivacyDescriptor, ProducerDescriptor, SupplementalArtifact
from tracecase_graph import GraphAssembler
from tracecase_invariants import InvariantRuntime

from .engine import PolicyEngine
from .models import ExportResult, RedactionPolicy
from .validation import ExportValidator


class ShareableBundleExporter:
    SAFE_COPIED_PREFIXES = ("specification/scenario_", "specification/expectations", "registry/")

    def __init__(self, policy: RedactionPolicy, *, token_key: bytes = b"tracecase-development-redaction-key") -> None:
        self.policy = policy
        self.engine = PolicyEngine(policy, token_key=token_key)
        self.validator = ExportValidator()

    def export(self, reader: BundleReader, output_path: Path, *, archive_path: Path | None = None, overwrite: bool = False) -> ExportResult:
        source_case = reader.load_case()
        sanitized_case, redaction = self.engine.apply(source_case)
        omitted = tuple(sorted(entry.path for entry in reader.content_index.entries if not self._safe_to_copy(entry.path)))
        validation = self.validator.validate_case(sanitized_case, self.policy, omitted_artifacts=omitted)
        if not redaction.valid_for_export or not validation.valid:
            raise ValueError("case does not satisfy export policy")

        graph = GraphAssembler().assemble(sanitized_case.evidence.execution)
        timeline = GraphAssembler().timeline(graph, sanitized_case.system)
        invariant_report = InvariantRuntime().evaluate(sanitized_case, graph)
        analysis = AnalyzerEngine().analyze(sanitized_case, graph)
        supplements = [
            SupplementalArtifact("policy/redaction_policy.json", self.policy),
            SupplementalArtifact("policy/redaction_report.json", redaction),
            SupplementalArtifact("policy/export_validation.json", validation),
            SupplementalArtifact("analysis/assembled_graph.json", graph),
            SupplementalArtifact("analysis/timeline.json", timeline),
            SupplementalArtifact("analysis/invariant_results.json", invariant_report),
            SupplementalArtifact("analysis/analysis_report.json", analysis),
        ]
        for entry in reader.content_index.entries:
            if self._safe_to_copy(entry.path):
                if entry.media_type == "application/x-ndjson":
                    supplements.append(SupplementalArtifact(entry.path, tuple(reader.read_jsonl(entry.path)), json_lines=True))
                else:
                    supplements.append(SupplementalArtifact(entry.path, reader.read_json(entry.path)))

        exported_case = sanitized_case.model_copy(update={
            "specification": sanitized_case.specification.model_copy(update={
                "case_id": f"case.shareable.{source_case.specification.case_id.replace('.', '-')}",
                "title": f"Shareable: {source_case.specification.title}",
                "privacy_policy_ref": self.policy.policy_id,
                "baseline_case_refs": (),
            })
        })
        builder = BundleBuilder(output_path, producer=ProducerDescriptor(name="tracecase", version="0.4.0"))
        result = builder.build(
            exported_case, overwrite=overwrite, supplements=supplements,
            profiles=(BundleProfile.EVIDENCE, BundleProfile.ANALYZED, BundleProfile.SHAREABLE, BundleProfile.REPRODUCIBLE),
            analysis_status="complete",
            privacy=PrivacyDescriptor(
                classification=self.policy.profile.value,
                redaction_policy_ref="policy/redaction_policy.json",
                validation_ref="policy/export_validation.json",
            ),
        )
        archive = builder.pack(archive_path, overwrite=overwrite) if archive_path else None
        verification = BundleReader(result.bundle_path).verify()
        validation = validation.model_copy(update={"integrity_valid": verification.valid})
        return ExportResult(
            source_case_id=source_case.specification.case_id, exported_case_id=exported_case.specification.case_id,
            bundle_path=str(result.bundle_path), archive_path=str(archive) if archive else None,
            policy_ref=self.policy.policy_id, redaction_report=redaction, validation_report=validation,
        )

    def _safe_to_copy(self, path: str) -> bool:
        return any(path.startswith(prefix) for prefix in self.SAFE_COPIED_PREFIXES)
