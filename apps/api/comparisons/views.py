from __future__ import annotations

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from cases.services import CaseRepository
from tracecase_compare import SemanticComparisonEngine

repository = CaseRepository()


@api_view(["POST"])
def compare_cases(request):
    baseline_case_id = request.data.get("baseline_case_id")
    candidate_case_id = request.data.get("candidate_case_id")
    if not baseline_case_id or not candidate_case_id:
        return Response(
            {"detail": "baseline_case_id and candidate_case_id are required"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    try:
        baseline_reader = repository.get_reader(str(baseline_case_id))
        candidate_reader = repository.get_reader(str(candidate_case_id))
        baseline_case = baseline_reader.load_case()
        candidate_case = candidate_reader.load_case()
        comparison = SemanticComparisonEngine().compare(
            baseline_case,
            repository.get_assembled_graph(str(baseline_case_id)),
            candidate_case,
            repository.get_assembled_graph(str(candidate_case_id)),
        )
    except FileNotFoundError as exc:
        return Response(
            {"detail": f"Case not found: {exc}"},
            status=status.HTTP_404_NOT_FOUND,
        )
    return Response(comparison.model_dump(mode="json"))
