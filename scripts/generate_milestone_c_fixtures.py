from __future__ import annotations

import json
import shutil
from pathlib import Path

from tracecase_analyzers import AnalyzerEngine, build_default_analyzer_registry
from tracecase_bundle import BundleBuilder, BundleProfile, ScenarioDescriptor, SupplementalArtifact
from tracecase_compare import SemanticComparisonEngine
from tracecase_graph import GraphAssembler
from tracecase_invariants import build_default_invariant_registry
from tracecase_model import CaseCategory
from tracecase_scenarios import (
    FaultApplication,
    FaultTargetKind,
    ScenarioDefinition,
    ScenarioGenerator,
    SyntheticExecutionEngine,
    build_default_registry,
)

ROOT = Path(__file__).resolve().parents[1]
BUNDLE_ROOT = ROOT / "fixtures" / "bundles"
REGISTRY_ROOT = ROOT / "registries"


def _definition(name: str, title: str, *, duplicate: bool = False, causal_gap: bool = False, context_drop: bool = False) -> ScenarioDefinition:
    if duplicate:
        family = "family.effect.duplicate.v1"
        faults = (
            FaultApplication(
                application_id=f"application.{name}.duplicate-effect.v1",
                operator_ref="fault.duplicate-effect.v1",
                target_kind=FaultTargetKind.EFFECT,
                parameters={"copies": 2},
            ),
        )
    elif causal_gap:
        family = "family.observability.causal-gap.v1"
        faults = (
            FaultApplication(
                application_id=f"application.{name}.break-trace.v1",
                operator_ref="fault.break-trace-link.v1",
                target_kind=FaultTargetKind.EDGE,
                target_ref="relation.synthetic.edge.publish-consume",
            ),
        )
    else:
        family = "family.continuity.context-disappearance.v1"
        faults = (
            FaultApplication(
                application_id=f"application.{name}.context-drop.v1",
                operator_ref="fault.drop-context.v1",
                target_kind=FaultTargetKind.ROLE,
                target_ref="role.consume",
            ),
        ) if context_drop else ()
    return ScenarioDefinition(
        scenario_id=f"scenario.{name}.v1",
        title=title,
        family_ref=family,
        faults=faults,
    )


def definitions() -> tuple[ScenarioDefinition, ...]:
    return (
        _definition("context-analysis-baseline", "Analyzed context continuity baseline"),
        _definition("context-analysis-failure", "Analyzed required-context failure", context_drop=True),
        _definition("duplicate-effect-analysis", "Analyzed duplicate durable effect", duplicate=True),
        _definition("causal-gap-analysis", "Analyzed observability causal gap", causal_gap=True),
    )


def export_registries() -> None:
    invariant_registry = build_default_invariant_registry()
    analyzer_registry = build_default_analyzer_registry()
    values = {
        REGISTRY_ROOT / "invariants" / "runtime.json": [item.model_dump(mode="json") for item in invariant_registry],
        REGISTRY_ROOT / "analyzers" / "core.json": [item.model_dump(mode="json") for item in analyzer_registry],
        REGISTRY_ROOT / "comparison" / "semantic.json": {
            "engine": "tracecase.semantic-comparison.v1",
            "version": "0.3.0",
            "alignment_basis": [
                "topology role and ordinal attempt",
                "normalized operation",
                "node kind",
                "component kind and role",
                "logical operation identity",
                "task name",
                "topology stage",
            ],
            "ignored_noise": [
                "regenerated trace identifiers",
                "regenerated workflow identifiers",
                "harmless timestamp jitter",
                "reordered concurrent observations",
            ],
            "dimensions": [
                "structure", "identity", "context", "timing", "state", "effect", "error", "resource", "deployment", "evidence"
            ],
        },
    }
    for path, value in values.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _supplements(definition, instance, run, family, topology, graph, timeline, analysis):
    derived_refs = set(graph.derived_relation_refs)
    derived_relations = [item for item in graph.relations if item.relation_id in derived_refs]
    return (
        SupplementalArtifact("specification/scenario_definition.json", definition),
        SupplementalArtifact("specification/scenario_instance.json", instance),
        SupplementalArtifact("specification/expectations.json", run.oracle_outcomes),
        SupplementalArtifact("registry/scenario_family.json", family),
        SupplementalArtifact("registry/topology.json", topology),
        SupplementalArtifact("registry/fault_operators.json", [build_default_registry().fault_operator(item.operator_ref) for item in instance.faults]),
        SupplementalArtifact("synthetic/ground_truth_case.json", run.ground_truth_case),
        SupplementalArtifact("synthetic/run_metadata.json", {
            "semantic_faults": run.semantic_faults,
            "observability_faults": run.observability_faults,
            "coverage_points": run.coverage_points,
            "attributes": run.attributes,
        }),
        SupplementalArtifact("analysis/assembled_graph.json", graph),
        SupplementalArtifact("analysis/graph_assembly_report.json", graph.report),
        SupplementalArtifact("analysis/timeline.json", timeline),
        SupplementalArtifact("analysis/invariant_results.json", analysis.invariant_report),
        SupplementalArtifact("analysis/findings.jsonl", analysis.findings, json_lines=True),
        SupplementalArtifact("analysis/analysis_runs.json", analysis.analyzer_runs),
        SupplementalArtifact("analysis/analysis_report.json", analysis),
        SupplementalArtifact("model/derived_relations.jsonl", derived_relations, json_lines=True),
        SupplementalArtifact("model/identity_groups.jsonl", graph.identity_groups, json_lines=True),
        SupplementalArtifact("model/context_flows.jsonl", graph.context_flows, json_lines=True),
        SupplementalArtifact("model/effect_groups.jsonl", graph.effect_groups, json_lines=True),
        SupplementalArtifact("model/temporal_constraints.jsonl", graph.temporal_constraints, json_lines=True),
    )


def build_analyzed_fixture(definition: ScenarioDefinition, *, seed: int):
    registry = build_default_registry()
    family = registry.family(definition.family_ref)
    topology = registry.topology(family.topology_ref)
    instance = ScenarioGenerator(registry).resolve(definition, seed=seed)
    run = SyntheticExecutionEngine(registry).realize(instance, title=definition.title)
    assembler = GraphAssembler()
    graph = assembler.assemble(run.observed_case.evidence.execution)
    timeline = assembler.timeline(graph, run.observed_case.system)
    analysis = AnalyzerEngine().analyze(run.observed_case, graph)
    stem = definition.scenario_id.removeprefix("scenario.").removesuffix(".v1")
    directory = BUNDLE_ROOT / f"{stem}.tracecase"
    archive = BUNDLE_ROOT / f"{stem}.tracecase.zip"
    if directory.exists(): shutil.rmtree(directory)
    if archive.exists(): archive.unlink()
    builder = BundleBuilder(directory)
    builder.build(
        run.observed_case,
        supplements=_supplements(definition, instance, run, family, topology, graph, timeline, analysis),
        profiles=(BundleProfile.EVIDENCE, BundleProfile.REPRODUCIBLE, BundleProfile.SYNTHETIC_BENCHMARK, BundleProfile.ANALYZED),
        scenario=ScenarioDescriptor(
            family_ref=instance.family_ref,
            definition_ref="specification/scenario_definition.json",
            instance_ref="specification/scenario_instance.json",
            expectations_ref="specification/expectations.json",
        ),
        analysis_status="complete",
    )
    builder.pack(archive)
    return run.observed_case, graph, analysis, directory, archive


def build_comparison_fixture(baseline_case, baseline_graph, candidate_case, candidate_graph) -> tuple[Path, Path]:
    comparison = SemanticComparisonEngine().compare(baseline_case, baseline_graph, candidate_case, candidate_graph)
    spec = candidate_case.specification.model_copy(update={
        "case_id": "case.semantic-context-comparison.v1",
        "title": "Semantic context-divergence comparison",
        "description": "Portable comparison of an intact execution and a required-context failure.",
        "category": CaseCategory.COMPARISON,
        "baseline_case_refs": (baseline_case.specification.case_id, candidate_case.specification.case_id),
    })
    comparison_case = candidate_case.model_copy(update={"specification": spec})
    directory = BUNDLE_ROOT / "semantic-context-comparison.tracecase"
    archive = BUNDLE_ROOT / "semantic-context-comparison.tracecase.zip"
    if directory.exists(): shutil.rmtree(directory)
    if archive.exists(): archive.unlink()
    supplements = (
        SupplementalArtifact("comparison/case_refs.json", {
            "baseline": comparison.baseline,
            "candidate": comparison.candidate,
        }),
        SupplementalArtifact("comparison/alignments.jsonl", comparison.alignments, json_lines=True),
        SupplementalArtifact("comparison/divergences.jsonl", comparison.divergences, json_lines=True),
        SupplementalArtifact("comparison/comparison_summary.json", comparison.summary),
        SupplementalArtifact("comparison/semantic_comparison.json", comparison),
        SupplementalArtifact("analysis/assembled_graph.json", candidate_graph),
        SupplementalArtifact("analysis/timeline.json", GraphAssembler().timeline(candidate_graph, candidate_case.system)),
    )
    builder = BundleBuilder(directory)
    builder.build(
        comparison_case,
        supplements=supplements,
        profiles=(BundleProfile.EVIDENCE, BundleProfile.REPRODUCIBLE, BundleProfile.ANALYZED, BundleProfile.COMPARISON),
        analysis_status="comparison_complete",
    )
    builder.pack(archive)
    return directory, archive


def main() -> None:
    export_registries()
    built = []
    for seed, definition in enumerate(definitions(), start=301):
        result = build_analyzed_fixture(definition, seed=seed)
        built.append(result)
        print(f"Generated {result[3].relative_to(ROOT)}")
        print(f"Generated {result[4].relative_to(ROOT)}")
    directory, archive = build_comparison_fixture(built[0][0], built[0][1], built[1][0], built[1][1])
    print(f"Generated {directory.relative_to(ROOT)}")
    print(f"Generated {archive.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
