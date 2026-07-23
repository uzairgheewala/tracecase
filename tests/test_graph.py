from __future__ import annotations

from tracecase_graph import GraphAssembler
from tracecase_scenarios import (
    FaultApplication,
    FaultTargetKind,
    ScenarioDefinition,
    ScenarioGenerator,
    SyntheticExecutionEngine,
    build_default_registry,
)


def _run_duplicate_effect():
    registry = build_default_registry()
    definition = ScenarioDefinition(
        scenario_id="scenario.test.graph-duplicate.v1",
        title="Duplicate effect graph",
        family_ref="family.effect.duplicate.v1",
        faults=(
            FaultApplication(
                application_id="application.test.graph-duplicate.v1",
                operator_ref="fault.duplicate-effect.v1",
                target_kind=FaultTargetKind.EFFECT,
                parameters={"copies": 2},
            ),
        ),
    )
    instance = ScenarioGenerator(registry).resolve(definition, seed=1)
    return SyntheticExecutionEngine(registry).realize(instance)


def test_graph_assembly_derives_identity_retry_and_effect_groups() -> None:
    run = _run_duplicate_effect()
    graph = GraphAssembler().assemble(run.observed_case.evidence.execution)
    assert graph.report.derived_relation_count > 0
    assert any(group.kind.value == "workflow" for group in graph.identity_groups)
    assert any(group.durable_count == 2 for group in graph.effect_groups)
    assert any(relation.kind.value == "retries" for relation in graph.relations)
    assert graph.report.source_relation_count == len(run.observed_case.evidence.execution.relations)


def test_timeline_uses_component_lanes_and_semantic_connectors() -> None:
    run = _run_duplicate_effect()
    assembler = GraphAssembler()
    graph = assembler.assemble(run.observed_case.evidence.execution)
    timeline = assembler.timeline(graph, run.observed_case.system)
    assert timeline.total_duration_ms > 0
    assert len(timeline.lanes) >= 3
    assert timeline.connectors
