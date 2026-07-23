from __future__ import annotations

from tracecase_scenarios import (
    FaultApplication,
    FaultTargetKind,
    ScenarioDefinition,
    ScenarioGenerator,
    build_default_registry,
)


def _definition() -> ScenarioDefinition:
    return ScenarioDefinition(
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


def test_default_registry_is_referentially_complete() -> None:
    registry = build_default_registry()
    assert len(registry.families) == 14
    assert len(registry.fault_operators) == 17
    assert registry.family("family.effect.duplicate.v1").topology_ref == "topology.async-effect.v1"


def test_instance_generation_is_deterministic() -> None:
    generator = ScenarioGenerator(build_default_registry())
    first = generator.resolve(_definition(), seed=11)
    second = generator.resolve(_definition(), seed=11)
    assert first == second
    assert first.instance_digest.startswith("sha256:")
    assert "family:family.continuity.context-disappearance.v1" in first.coverage_points


def test_pairwise_generation_covers_all_admissible_pairs() -> None:
    generator = ScenarioGenerator(build_default_registry())
    batch = generator.pairwise(_definition(), seed=3)
    exhaustive = generator.constrained_exhaustive(_definition(), seed=3)
    expected_pairs = {
        pair
        for instance in exhaustive.instances
        for pair in generator._instance_pairs(instance)  # test the public behavior through complete pair coverage
    }
    actual_pairs = {
        pair
        for instance in batch.instances
        for pair in generator._instance_pairs(instance)
    }
    assert expected_pairs <= actual_pairs
    assert len(batch.instances) <= len(exhaustive.instances)
