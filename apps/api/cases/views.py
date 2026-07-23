from __future__ import annotations

from dataclasses import asdict

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from .services import CaseRepository

repository = CaseRepository()


@api_view(["GET"])
def case_list(_request):
    return Response({"items": [asdict(item) for item in repository.list()]})


@api_view(["GET"])
def case_detail(_request, case_id: str):
    try:
        reader = repository.get_reader(case_id)
    except FileNotFoundError:
        return Response({"detail": "Case not found"}, status=status.HTTP_404_NOT_FOUND)
    case = reader.load_case()
    return Response({
        "manifest": reader.manifest.model_dump(mode="json"),
        "specification": case.specification.model_dump(mode="json"),
        "system": case.system.model_dump(mode="json"),
        "summary": {
            "nodes": len(case.evidence.execution.nodes),
            "relations": len(case.evidence.execution.relations),
            "contexts": len(case.evidence.execution.contexts),
            "state_facts": len(case.evidence.execution.state_facts),
            "effects": len(case.evidence.execution.effects),
            "observations": len(case.evidence.execution.observations),
        },
    })


@api_view(["GET"])
def case_graph(_request, case_id: str):
    try:
        case = repository.get_reader(case_id).load_case()
    except FileNotFoundError:
        return Response({"detail": "Case not found"}, status=status.HTTP_404_NOT_FOUND)
    execution = case.evidence.execution
    return Response({
        "nodes": [node.model_dump(mode="json") for node in execution.nodes],
        "relations": [relation.model_dump(mode="json") for relation in execution.relations],
        "contexts": [context.model_dump(mode="json") for context in execution.contexts],
        "state_facts": [fact.model_dump(mode="json") for fact in execution.state_facts],
        "effects": [effect.model_dump(mode="json") for effect in execution.effects],
    })


@api_view(["GET"])
def case_validation(_request, case_id: str):
    try:
        reader = repository.get_reader(case_id)
    except FileNotFoundError:
        return Response({"detail": "Case not found"}, status=status.HTTP_404_NOT_FOUND)
    return Response(reader.validation_report().model_dump(mode="json"))
