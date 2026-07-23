from __future__ import annotations

from pathlib import Path

from tracecase_bundle import (
    BundleBuilder,
    BundleProfile,
    BundleReader,
    ScenarioDescriptor,
    SupplementalArtifact,
)
from tracecase_graph import GraphAssembler
from tracecase_scenarios import ScenarioDefinition, ScenarioGenerator, SyntheticExecutionEngine, build_default_registry


def test_bundle_supports_opaque_scenario_and_graph_artifacts(tmp_path: Path) -> None:
    registry = build_default_registry()
    definition = ScenarioDefinition(
        scenario_id="scenario.test.bundle-baseline.v1",
        title="Bundle baseline",
        family_ref="family.continuity.context-disappearance.v1",
    )
    instance = ScenarioGenerator(registry).resolve(definition, seed=4)
    run = SyntheticExecutionEngine(registry).realize(instance)
    assembler = GraphAssembler()
    graph = assembler.assemble(run.observed_case.evidence.execution)
    timeline = assembler.timeline(graph, run.observed_case.system)
    output = tmp_path / "synthetic.tracecase"
    builder = BundleBuilder(output)
    builder.build(
        run.observed_case,
        supplements=(
            SupplementalArtifact("specification/scenario_definition.json", definition),
            SupplementalArtifact("specification/scenario_instance.json", instance),
            SupplementalArtifact("synthetic/ground_truth_case.json", run.ground_truth_case),
            SupplementalArtifact("analysis/assembled_graph.json", graph),
            SupplementalArtifact("analysis/timeline.json", timeline),
            SupplementalArtifact("analysis/graph_assembly_report.json", graph.report),
        ),
        profiles=(
            BundleProfile.EVIDENCE,
            BundleProfile.REPRODUCIBLE,
            BundleProfile.SYNTHETIC_BENCHMARK,
            BundleProfile.ANALYZED,
        ),
        scenario=ScenarioDescriptor(
            family_ref=instance.family_ref,
            definition_ref="specification/scenario_definition.json",
            instance_ref="specification/scenario_instance.json",
        ),
        analysis_status="assembled",
    )
    reader = BundleReader(output)
    assert reader.verify().valid
    assert reader.has_artifact("analysis/assembled_graph.json")
    assert reader.manifest.scenario is not None
    assert reader.manifest.scenario.family_ref == instance.family_ref
