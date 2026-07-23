from rest_framework.decorators import api_view
from rest_framework.response import Response
from tracecase_coverage import CoverageEngine
from tracecase_scenarios import FaultApplication,FaultTargetKind,ScenarioDefinition,ScenarioGenerator,build_default_registry

def build_report():
    registry=build_default_registry(); generator=ScenarioGenerator(registry); instances=[]
    for index,family in enumerate(registry.families):
        definition=ScenarioDefinition(scenario_id=f"scenario.api.coverage.{index}",title=family.title,family_ref=family.family_id)
        instances.append(generator.resolve(definition,seed=3000+index))
        if family.allowed_fault_operator_refs:
            application=FaultApplication(application_id=f"application.api.coverage.{index}",operator_ref=family.allowed_fault_operator_refs[0],target_kind=FaultTargetKind.SYSTEM)
            instances.append(generator.resolve(definition.model_copy(update={"faults":(application,)}),seed=4000+index))
    return CoverageEngine(registry).evaluate(instances)

@api_view(["GET"])
def coverage_report(_request):
    return Response(build_report().model_dump(mode="json"))
