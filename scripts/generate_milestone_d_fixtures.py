from __future__ import annotations

import json
import shutil
from pathlib import Path

from tracecase_bundle import (
    BundleBuilder,
    BundleProfile,
    BundleReader,
    PrivacyDescriptor,
    ProducerDescriptor,
    SupplementalArtifact,
)
from tracecase_lab import LabRunRequest, ReferenceLab, lab_bindings
from tracecase_model import CaseCategory
from tracecase_policy import ShareableBundleExporter, policy_registry, default_shareable_policy

ROOT = Path(__file__).resolve().parents[1]
BUNDLE_ROOT = ROOT / "fixtures" / "bundles"
REGISTRY_ROOT = ROOT / "registries"
PRODUCER = ProducerDescriptor(name="tracecase-reference-lab", version="0.4.0")


def export_registries() -> None:
    values = {
        REGISTRY_ROOT / "privacy" / "default-policies.json": [
            policy.model_dump(mode="json") for policy in policy_registry()
        ],
        REGISTRY_ROOT / "lab" / "reference-bindings.json": [
            binding.model_dump(mode="json") for binding in lab_bindings()
        ],
    }
    for path, value in values.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _clean(stem: str) -> tuple[Path, Path]:
    directory = BUNDLE_ROOT / f"{stem}.tracecase"
    archive = BUNDLE_ROOT / f"{stem}.tracecase.zip"
    if directory.exists():
        shutil.rmtree(directory)
    if archive.exists():
        archive.unlink()
    return directory, archive


def _run_supplements(result):
    derived_refs = set(result.graph.derived_relation_refs)
    derived_relations = tuple(
        relation for relation in result.graph.relations if relation.relation_id in derived_refs
    )
    return (
        SupplementalArtifact("registry/lab_binding.json", next(item for item in lab_bindings() if item.binding_id == result.receipt.binding_ref)),
        SupplementalArtifact("collection/lab_events.jsonl", result.events, json_lines=True),
        SupplementalArtifact("collection/lab_run_receipt.json", result.receipt),
        SupplementalArtifact("analysis/assembled_graph.json", result.graph),
        SupplementalArtifact("analysis/graph_assembly_report.json", result.graph.report),
        SupplementalArtifact("analysis/timeline.json", result.timeline),
        SupplementalArtifact("analysis/invariant_results.json", result.analysis.invariant_report),
        SupplementalArtifact("analysis/findings.jsonl", result.analysis.findings, json_lines=True),
        SupplementalArtifact("analysis/analysis_runs.json", result.analysis.analyzer_runs),
        SupplementalArtifact("analysis/analysis_report.json", result.analysis),
        SupplementalArtifact("model/derived_relations.jsonl", derived_relations, json_lines=True),
        SupplementalArtifact("model/identity_groups.jsonl", result.graph.identity_groups, json_lines=True),
        SupplementalArtifact("model/context_flows.jsonl", result.graph.context_flows, json_lines=True),
        SupplementalArtifact("model/effect_groups.jsonl", result.graph.effect_groups, json_lines=True),
        SupplementalArtifact("model/temporal_constraints.jsonl", result.graph.temporal_constraints, json_lines=True),
    )


def build_run(stem: str, request: LabRunRequest):
    result = ReferenceLab().run(request)
    directory, archive = _clean(stem)
    builder = BundleBuilder(directory, producer=PRODUCER)
    builder.build(
        result.case,
        overwrite=True,
        supplements=_run_supplements(result),
        profiles=(BundleProfile.EVIDENCE, BundleProfile.ANALYZED, BundleProfile.REPRODUCIBLE),
        analysis_status="complete",
        privacy=PrivacyDescriptor(classification="internal"),
    )
    builder.pack(archive, overwrite=True)
    return result, directory, archive


def build_comparison(stem: str, request: LabRunRequest):
    result = ReferenceLab().compare(request)
    comparison = result.comparison
    spec = result.candidate.case.specification.model_copy(update={
        "case_id": f"case.{stem.replace('-', '.')}.v1",
        "title": "Reference-lab context divergence comparison",
        "description": "Portable comparison of an intact concrete workflow and the same workflow with required tenant context removed at the worker boundary.",
        "category": CaseCategory.COMPARISON,
        "baseline_case_refs": (
            result.baseline.case.specification.case_id,
            result.candidate.case.specification.case_id,
        ),
    })
    case = result.candidate.case.model_copy(update={"specification": spec})
    directory, archive = _clean(stem)
    supplements = (
        SupplementalArtifact("registry/lab_binding.json", next(item for item in lab_bindings() if item.binding_id == request.binding_ref)),
        SupplementalArtifact("comparison/case_refs.json", {"baseline": comparison.baseline, "candidate": comparison.candidate}),
        SupplementalArtifact("comparison/alignments.jsonl", comparison.alignments, json_lines=True),
        SupplementalArtifact("comparison/divergences.jsonl", comparison.divergences, json_lines=True),
        SupplementalArtifact("comparison/comparison_summary.json", comparison.summary),
        SupplementalArtifact("comparison/semantic_comparison.json", comparison),
        SupplementalArtifact("comparison/baseline_receipt.json", result.baseline.receipt),
        SupplementalArtifact("comparison/candidate_receipt.json", result.candidate.receipt),
        SupplementalArtifact("comparison/baseline_events.jsonl", result.baseline.events, json_lines=True),
        SupplementalArtifact("comparison/candidate_events.jsonl", result.candidate.events, json_lines=True),
        SupplementalArtifact("analysis/assembled_graph.json", result.candidate.graph),
        SupplementalArtifact("analysis/timeline.json", result.candidate.timeline),
        SupplementalArtifact("analysis/invariant_results.json", result.candidate.analysis.invariant_report),
        SupplementalArtifact("analysis/findings.jsonl", result.candidate.analysis.findings, json_lines=True),
        SupplementalArtifact("analysis/analysis_report.json", result.candidate.analysis),
    )
    builder = BundleBuilder(directory, producer=PRODUCER)
    builder.build(
        case,
        overwrite=True,
        supplements=supplements,
        profiles=(BundleProfile.EVIDENCE, BundleProfile.ANALYZED, BundleProfile.REPRODUCIBLE, BundleProfile.COMPARISON),
        analysis_status="comparison_complete",
        privacy=PrivacyDescriptor(classification="internal"),
    )
    builder.pack(archive, overwrite=True)
    return result, directory, archive


def build_shareable(source_directory: Path, stem: str):
    directory, archive = _clean(stem)
    reader = BundleReader(source_directory)
    exporter = ShareableBundleExporter(
        default_shareable_policy(), token_key=b"tracecase-milestone-d-fixture-key"
    )
    result = exporter.export(reader, directory, archive_path=archive, overwrite=True)
    return result, directory, archive


def main() -> None:
    BUNDLE_ROOT.mkdir(parents=True, exist_ok=True)
    export_registries()
    lab = [
        ("reference-lab-baseline", LabRunRequest(seed=401)),
        ("reference-lab-context-loss", LabRunRequest(seed=402, fault_operator_ref="fault.context.drop.v1")),
        ("reference-lab-duplicate-effect", LabRunRequest(seed=403, fault_operator_ref="fault.effect.duplicate.v1")),
        ("reference-lab-publish-before-commit", LabRunRequest(seed=404, fault_operator_ref="fault.ordering.publish-before-commit.v1")),
        ("reference-lab-privacy-capture", LabRunRequest(seed=405, fault_operator_ref="fault.privacy.capture-secret.v1", include_sensitive_payload=True)),
        ("reference-lab-observability-gap", LabRunRequest(seed=406, observability_fault_ref="fault.observability.break-link.v1")),
    ]
    built: dict[str, tuple] = {}
    for stem, request in lab:
        value = build_run(stem, request)
        built[stem] = value
        print(f"Generated {value[1].relative_to(ROOT)}")
        print(f"Generated {value[2].relative_to(ROOT)}")

    comparison = build_comparison(
        "reference-lab-context-comparison",
        LabRunRequest(seed=407, fault_operator_ref="fault.context.drop.v1"),
    )
    print(f"Generated {comparison[1].relative_to(ROOT)}")
    print(f"Generated {comparison[2].relative_to(ROOT)}")

    shareable = build_shareable(
        built["reference-lab-privacy-capture"][1], "reference-lab-shareable"
    )
    print(f"Generated {shareable[1].relative_to(ROOT)}")
    print(f"Generated {shareable[2].relative_to(ROOT)}")


if __name__ == "__main__":
    main()
