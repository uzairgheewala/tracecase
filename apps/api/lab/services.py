from __future__ import annotations

from pathlib import Path
from django.conf import settings
from tracecase_bundle import BundleBuilder, BundleProfile, ProducerDescriptor, SupplementalArtifact
from tracecase_lab import LabRunRequest, ReferenceLab, lab_bindings


class LabService:
    def __init__(self) -> None:
        self.lab = ReferenceLab()

    def bindings(self):
        return lab_bindings()

    def run(self, payload: dict):
        request = LabRunRequest.model_validate(payload)
        return self.lab.run(request)

    def compare(self, payload: dict):
        request = LabRunRequest.model_validate(payload)
        return self.lab.compare(request)

    def persist(self, payload: dict):
        request = LabRunRequest.model_validate(payload)
        result = self.lab.run(request)
        root = Path(settings.TRACECASE_BUNDLE_ROOT)
        root.mkdir(parents=True, exist_ok=True)
        output = root / f"{result.case.specification.case_id}.tracecase"
        builder = BundleBuilder(output, producer=ProducerDescriptor(name="tracecase-reference-lab", version="0.4.0"))
        builder.build(
            result.case, overwrite=True, profiles=(BundleProfile.EVIDENCE, BundleProfile.ANALYZED, BundleProfile.REPRODUCIBLE),
            analysis_status="complete", supplements=(
                SupplementalArtifact("analysis/assembled_graph.json", result.graph),
                SupplementalArtifact("analysis/timeline.json", result.timeline),
                SupplementalArtifact("analysis/invariant_results.json", result.analysis.invariant_report),
                SupplementalArtifact("analysis/analysis_report.json", result.analysis),
                SupplementalArtifact("collection/lab_events.jsonl", result.events, json_lines=True),
                SupplementalArtifact("collection/lab_run_receipt.json", result.receipt),
            ),
        )
        archive = builder.pack(root / f"{result.case.specification.case_id}.tracecase.zip", overwrite=True)
        return result, output, archive
