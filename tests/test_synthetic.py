from __future__ import annotations

from tracecase_scenarios import (
    FaultApplication,
    FaultTargetKind,
    ScenarioDefinition,
    ScenarioGenerator,
    SyntheticExecutionEngine,
    build_default_registry,
)


def test_semantic_fault_changes_ground_truth_before_observability() -> None:
    registry = build_default_registry()
    definition = ScenarioDefinition(
        scenario_id="scenario.test.context-drop.v1",
        title="Context drop",
        family_ref="family.continuity.context-disappearance.v1",
        faults=(
            FaultApplication(
                application_id="application.test.drop-context.v1",
                operator_ref="fault.drop-context.v1",
                target_kind=FaultTargetKind.ROLE,
                target_ref="role.consume",
            ),
        ),
    )
    instance = ScenarioGenerator(registry).resolve(definition, seed=5)
    run = SyntheticExecutionEngine(registry).realize(instance)
    assert len(run.ground_truth_case.evidence.execution.contexts) == 4
    assert len(run.observed_case.evidence.execution.contexts) == 4
    assert run.oracle_outcomes[0].expected_status.value == "violated"


def test_observability_fault_preserves_ground_truth() -> None:
    registry = build_default_registry()
    definition = ScenarioDefinition(
        scenario_id="scenario.test.broken-trace.v1",
        title="Broken trace",
        family_ref="family.observability.causal-gap.v1",
        faults=(
            FaultApplication(
                application_id="application.test.break-trace.v1",
                operator_ref="fault.break-trace-link.v1",
                target_kind=FaultTargetKind.EDGE,
                target_ref="relation.synthetic.edge.publish-consume",
            ),
        ),
    )
    instance = ScenarioGenerator(registry).resolve(definition, seed=2)
    run = SyntheticExecutionEngine(registry).realize(instance)
    assert len(run.ground_truth_case.evidence.execution.relations) > len(
        run.observed_case.evidence.execution.relations
    )
    assert run.ground_truth_case.evidence.execution.extensions["tracecase.scenario"]["ground_truth"] is True


def test_duplicate_effect_creates_retry_attempt_and_effect_group_members() -> None:
    registry = build_default_registry()
    definition = ScenarioDefinition(
        scenario_id="scenario.test.duplicate-effect.v1",
        title="Duplicate effect",
        family_ref="family.effect.duplicate.v1",
        faults=(
            FaultApplication(
                application_id="application.test.duplicate-effect.v1",
                operator_ref="fault.duplicate-effect.v1",
                target_kind=FaultTargetKind.EFFECT,
                parameters={"copies": 3},
            ),
        ),
    )
    instance = ScenarioGenerator(registry).resolve(definition, seed=9)
    run = SyntheticExecutionEngine(registry).realize(instance)
    execution = run.ground_truth_case.evidence.execution
    assert len(execution.effects) == 3
    attempts = sorted(
        node.identities.task_attempt
        for node in execution.nodes
        if node.identities.task_attempt is not None
    )
    assert attempts == [1, 2, 3]
