from tracecase_coverage import CoverageEngine, MutationAdequacyEngine, MutationTrial, ScenarioMinimizer
from tracecase_scenarios import FaultApplication, FaultTargetKind, ScenarioDefinition, ScenarioGenerator, build_default_registry

def test_coverage_ledger_and_recommendations():
    registry=build_default_registry(); generator=ScenarioGenerator(registry); instances=[]
    for index,family in enumerate(registry.families):
        definition=ScenarioDefinition(scenario_id=f"scenario.coverage.{index}",title=family.title,family_ref=family.family_id)
        instances.append(generator.resolve(definition,seed=index))
        if family.allowed_fault_operator_refs:
            fault=FaultApplication(application_id=f"fault-app.{index}",operator_ref=family.allowed_fault_operator_refs[0],target_kind=FaultTargetKind.SYSTEM)
            instances.append(generator.resolve(definition.model_copy(update={"faults":(fault,)}),seed=100+index))
    report=CoverageEngine(registry).evaluate(instances)
    assert report.summary["covered"] >= len(registry.families)
    assert report.summary["uncovered"] > 0
    assert report.recommendations
    assert all(any(ref==p.point_id for p in report.points) for r in report.recommendations for ref in r.uncovered_point_refs)

def test_scenario_minimization_uses_external_preservation_oracle():
    essential=FaultApplication(application_id="fault.essential",operator_ref="fault.context.drop.v1",target_kind=FaultTargetKind.SYSTEM)
    extra=FaultApplication(application_id="fault.extra",operator_ref="fault.observability.break-link.v1",target_kind=FaultTargetKind.SYSTEM)
    definition=ScenarioDefinition(scenario_id="scenario.minimize",title="Minimize",family_ref="continuity.context_disappearance.v1",parameter_bindings={"x":1,"y":2},faults=(essential,extra))
    minimized,report=ScenarioMinimizer().minimize_definition(definition,target_ref="context.required_continuity.v1",preserves=lambda item:any(f.operator_ref=="fault.context.drop.v1" for f in item.faults))
    assert [f.operator_ref for f in minimized.faults]==["fault.context.drop.v1"]
    assert minimized.parameter_bindings=={}
    assert report.minimized_size < report.original_size

def test_mutation_adequacy_score():
    report=MutationAdequacyEngine().evaluate((MutationTrial(trial_id="trial.a",mutation_ref="drop",target_ref="x",detected=True),MutationTrial(trial_id="trial.b",mutation_ref="skew",target_ref="y",detected=False)))
    assert report.score==0.5 and report.survived==1
