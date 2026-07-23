from __future__ import annotations

from pydantic import ValidationError
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from tracecase_graph import GraphAssembler
from tracecase_scenarios import (
    ScenarioDefinition,
    ScenarioGenerator,
    SyntheticExecutionEngine,
    build_default_registry,
)

registry = build_default_registry()


@api_view(["GET"])
def family_list(_request):
    return Response(
        {
            "registry_version": registry.registry_version,
            "semantic_universe_version": registry.semantic_universe_version,
            "items": [
                {
                    "family_id": family.family_id,
                    "title": family.title,
                    "description": family.description,
                    "family_class": family.family_class.value,
                    "universe_axes": [axis.value for axis in family.universe_axes],
                    "topology_ref": family.topology_ref,
                    "parameter_domains": [item.model_dump(mode="json") for item in family.parameter_domains],
                    "fault_operators": list(family.allowed_fault_operator_refs),
                    "invariants": list(family.invariant_refs),
                    "observability_profiles": [item.value for item in family.observability_profiles],
                }
                for family in registry.families
            ],
        }
    )


@api_view(["GET"])
def family_detail(_request, family_id: str):
    try:
        family = registry.family(family_id)
        topology = registry.topology(family.topology_ref)
    except KeyError:
        return Response({"detail": "Scenario family not found"}, status=status.HTTP_404_NOT_FOUND)
    return Response(
        {
            "family": family.model_dump(mode="json"),
            "topology": topology.model_dump(mode="json"),
            "fault_operators": [
                registry.fault_operator(item).model_dump(mode="json")
                for item in family.allowed_fault_operator_refs
            ],
            "invariants": {
                item: registry.invariant_catalog[item] for item in family.invariant_refs
            },
        }
    )


@api_view(["POST"])
def generate(_request):
    payload = dict(_request.data)
    try:
        definition = ScenarioDefinition.model_validate(
            {
                "scenario_id": payload.get("scenario_id", "scenario.workbench.generated.v1"),
                "title": payload.get("title", "Workbench generated scenario"),
                "family_ref": payload["family_ref"],
                "parameter_bindings": payload.get("parameter_bindings", {}),
                "faults": payload.get("faults", []),
                "observability_profile": payload.get("observability_profile", "complete"),
                "expected_invariants": payload.get("expected_invariants", []),
            }
        )
        seed = int(payload.get("seed", 0))
        instance = ScenarioGenerator(registry).resolve(definition, seed=seed)
        run = SyntheticExecutionEngine(registry).realize(instance)
        assembler = GraphAssembler()
        graph = assembler.assemble(run.observed_case.evidence.execution)
        timeline = assembler.timeline(graph, run.observed_case.system)
    except (KeyError, ValueError, ValidationError) as exc:
        details = exc.errors() if isinstance(exc, ValidationError) else str(exc)
        return Response(
            {"detail": "Scenario generation failed", "errors": details},
            status=status.HTTP_400_BAD_REQUEST,
        )
    return Response(
        {
            "definition": definition.model_dump(mode="json"),
            "instance": instance.model_dump(mode="json"),
            "oracle": [item.model_dump(mode="json") for item in run.oracle_outcomes],
            "ground_truth_summary": {
                "nodes": len(run.ground_truth_case.evidence.execution.nodes),
                "relations": len(run.ground_truth_case.evidence.execution.relations),
                "contexts": len(run.ground_truth_case.evidence.execution.contexts),
                "effects": len(run.ground_truth_case.evidence.execution.effects),
                "observations": len(run.ground_truth_case.evidence.execution.observations),
            },
            "observed_case": {
                "specification": run.observed_case.specification.model_dump(mode="json"),
                "system": run.observed_case.system.model_dump(mode="json"),
                "execution": run.observed_case.evidence.execution.model_dump(mode="json"),
            },
            "graph": graph.model_dump(mode="json"),
            "timeline": timeline.model_dump(mode="json"),
        }
    )
