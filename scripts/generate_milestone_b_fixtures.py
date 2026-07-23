from __future__ import annotations

import json
import shutil
from pathlib import Path

from tracecase_bundle import (
    BundleBuilder,
    BundleProfile,
    ScenarioDescriptor,
    SupplementalArtifact,
)
from tracecase_graph import GraphAssembler
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


def definitions() -> tuple[ScenarioDefinition, ...]:
    return (
        ScenarioDefinition(
            scenario_id="scenario.context-continuity-baseline.v1",
            title="Context continuity baseline",
            family_ref="family.continuity.context-disappearance.v1",
        ),
        ScenarioDefinition(
            scenario_id="scenario.context-continuity-failure.v1",
            title="Required context disappears at the consumer",
            family_ref="family.continuity.context-disappearance.v1",
            faults=(
                FaultApplication(
                    application_id="application.context-drop.v1",
                    operator_ref="fault.drop-context.v1",
                    target_kind=FaultTargetKind.ROLE,
                    target_ref="role.consume",
                ),
            ),
        ),
        ScenarioDefinition(
            scenario_id="scenario.duplicate-effect-failure.v1",
            title="Retry repeats a durable logical effect",
            family_ref="family.effect.duplicate.v1",
            faults=(
                FaultApplication(
                    application_id="application.duplicate-effect.v1",
                    operator_ref="fault.duplicate-effect.v1",
                    target_kind=FaultTargetKind.EFFECT,
                    parameters={"copies": 2},
                ),
            ),
        ),
        ScenarioDefinition(
            scenario_id="scenario.causal-gap-observed.v1",
            title="Async execution with a missing causal link",
            family_ref="family.observability.causal-gap.v1",
            faults=(
                FaultApplication(
                    application_id="application.break-trace.v1",
                    operator_ref="fault.break-trace-link.v1",
                    target_kind=FaultTargetKind.EDGE,
                    target_ref="relation.synthetic.edge.publish-consume",
                ),
            ),
        ),
    )


def export_registry() -> None:
    registry = build_default_registry()
    paths = {
        REGISTRY_ROOT / "scenario-families" / "core.json": [
            item.model_dump(mode="json") for item in registry.families
        ],
        REGISTRY_ROOT / "fault-operators" / "core.json": [
            item.model_dump(mode="json") for item in registry.fault_operators
        ],
        REGISTRY_ROOT / "topology-motifs" / "core.json": [
            item.model_dump(mode="json") for item in registry.topologies
        ],
        REGISTRY_ROOT / "invariants" / "core.json": registry.invariant_catalog,
        REGISTRY_ROOT / "registry.json": registry.model_dump(mode="json"),
    }
    for path, value in paths.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def build_fixture(definition: ScenarioDefinition, *, seed: int) -> tuple[Path, Path]:
    registry = build_default_registry()
    family = registry.family(definition.family_ref)
    topology = registry.topology(family.topology_ref)
    generator = ScenarioGenerator(registry)
    instance = generator.resolve(definition, seed=seed)
    run = SyntheticExecutionEngine(registry).realize(instance, title=definition.title)
    assembler = GraphAssembler()
    graph = assembler.assemble(run.observed_case.evidence.execution)
    timeline = assembler.timeline(graph, run.observed_case.system)

    stem = definition.scenario_id.removeprefix("scenario.").removesuffix(".v1")
    directory = BUNDLE_ROOT / f"{stem}.tracecase"
    archive = BUNDLE_ROOT / f"{stem}.tracecase.zip"
    if directory.exists():
        shutil.rmtree(directory)
    if archive.exists():
        archive.unlink()

    derived_relations = [
        relation
        for relation in graph.relations
        if relation.relation_id in set(graph.derived_relation_refs)
    ]
    supplements = (
        SupplementalArtifact("specification/scenario_definition.json", definition),
        SupplementalArtifact("specification/scenario_instance.json", instance),
        SupplementalArtifact("specification/expectations.json", run.oracle_outcomes),
        SupplementalArtifact("registry/scenario_family.json", family),
        SupplementalArtifact("registry/topology.json", topology),
        SupplementalArtifact(
            "registry/fault_operators.json",
            [registry.fault_operator(item.operator_ref) for item in instance.faults],
        ),
        SupplementalArtifact("synthetic/ground_truth_case.json", run.ground_truth_case),
        SupplementalArtifact(
            "synthetic/run_metadata.json",
            {
                "semantic_faults": run.semantic_faults,
                "observability_faults": run.observability_faults,
                "coverage_points": run.coverage_points,
                "attributes": run.attributes,
            },
        ),
        SupplementalArtifact("analysis/assembled_graph.json", graph),
        SupplementalArtifact("analysis/graph_assembly_report.json", graph.report),
        SupplementalArtifact("analysis/timeline.json", timeline),
        SupplementalArtifact("model/derived_relations.jsonl", derived_relations, json_lines=True),
        SupplementalArtifact("model/identity_groups.jsonl", graph.identity_groups, json_lines=True),
        SupplementalArtifact("model/context_flows.jsonl", graph.context_flows, json_lines=True),
        SupplementalArtifact("model/effect_groups.jsonl", graph.effect_groups, json_lines=True),
        SupplementalArtifact(
            "model/temporal_constraints.jsonl",
            graph.temporal_constraints,
            json_lines=True,
        ),
    )
    builder = BundleBuilder(directory)
    builder.build(
        run.observed_case,
        supplements=supplements,
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
            expectations_ref="specification/expectations.json",
        ),
        analysis_status="assembled",
    )
    builder.pack(archive)
    return directory, archive


def main() -> None:
    export_registry()
    for seed, definition in enumerate(definitions(), start=101):
        directory, archive = build_fixture(definition, seed=seed)
        print(f"Generated {directory.relative_to(ROOT)}")
        print(f"Generated {archive.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
