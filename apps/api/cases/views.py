from __future__ import annotations

from dataclasses import asdict

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .services import CaseRepository

repository = CaseRepository()


@api_view(["GET"])
def case_list(_request):
    return Response({"items": [asdict(item) for item in repository.list()]})


@api_view(["GET"])
def case_detail(_request, case_id: str):
    try:
        reader = repository.get_reader(case_id)
        graph = repository.get_assembled_graph(case_id)
        analysis = repository.get_analysis_report(case_id)
    except FileNotFoundError:
        return Response({"detail": "Case not found"}, status=status.HTTP_404_NOT_FOUND)
    case = reader.load_case()
    return Response(
        {
            "manifest": reader.manifest.model_dump(mode="json"),
            "specification": case.specification.model_dump(mode="json"),
            "system": case.system.model_dump(mode="json"),
            "summary": {
                "nodes": len(case.evidence.execution.nodes),
                "source_relations": len(case.evidence.execution.relations),
                "relations": len(graph.relations),
                "derived_relations": graph.report.derived_relation_count,
                "contexts": len(case.evidence.execution.contexts),
                "context_flows": len(graph.context_flows),
                "state_facts": len(case.evidence.execution.state_facts),
                "effects": len(case.evidence.execution.effects),
                "effect_groups": len(graph.effect_groups),
                "observations": len(case.evidence.execution.observations),
                "warnings": len(graph.report.warnings),
                "invariant_results": len(analysis.invariant_report.results),
                "violated_invariants": sum(
                    item.status.value in {"violated", "contradicted"}
                    for item in analysis.invariant_report.results
                ),
                "findings": len(analysis.findings),
            },
            "scenario": (
                reader.read_optional_json("specification/scenario_instance.json")
                if reader.manifest.scenario
                else None
            ),
            "oracle": reader.read_optional_json("specification/expectations.json"),
            "ground_truth_available": reader.has_artifact("synthetic/ground_truth_case.json"),
        }
    )


@api_view(["GET"])
def case_graph(_request, case_id: str):
    try:
        case = repository.get_reader(case_id).load_case()
    except FileNotFoundError:
        return Response({"detail": "Case not found"}, status=status.HTTP_404_NOT_FOUND)
    execution = case.evidence.execution
    return Response(
        {
            "nodes": [node.model_dump(mode="json") for node in execution.nodes],
            "relations": [relation.model_dump(mode="json") for relation in execution.relations],
            "contexts": [context.model_dump(mode="json") for context in execution.contexts],
            "state_facts": [fact.model_dump(mode="json") for fact in execution.state_facts],
            "effects": [effect.model_dump(mode="json") for effect in execution.effects],
        }
    )


@api_view(["GET"])
def case_assembled_graph(_request, case_id: str):
    try:
        graph = repository.get_assembled_graph(case_id)
        analysis = repository.get_analysis_report(case_id)
    except FileNotFoundError:
        return Response({"detail": "Case not found"}, status=status.HTTP_404_NOT_FOUND)
    return Response(graph.model_dump(mode="json"))


@api_view(["GET"])
def case_timeline(_request, case_id: str):
    try:
        timeline = repository.get_timeline(case_id)
    except FileNotFoundError:
        return Response({"detail": "Case not found"}, status=status.HTTP_404_NOT_FOUND)
    return Response(timeline.model_dump(mode="json"))


@api_view(["GET"])
def case_validation(_request, case_id: str):
    try:
        reader = repository.get_reader(case_id)
    except FileNotFoundError:
        return Response({"detail": "Case not found"}, status=status.HTTP_404_NOT_FOUND)
    return Response(reader.validation_report().model_dump(mode="json"))


@api_view(["GET"])
def case_invariants(_request, case_id: str):
    try:
        report = repository.get_invariant_report(case_id)
    except FileNotFoundError:
        return Response({"detail": "Case not found"}, status=status.HTTP_404_NOT_FOUND)
    return Response(report.model_dump(mode="json"))


@api_view(["GET"])
def case_analysis(_request, case_id: str):
    try:
        report = repository.get_analysis_report(case_id)
    except FileNotFoundError:
        return Response({"detail": "Case not found"}, status=status.HTTP_404_NOT_FOUND)
    return Response(report.model_dump(mode="json"))
