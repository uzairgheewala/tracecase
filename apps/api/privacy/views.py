from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .services import PrivacyService

service = PrivacyService()

@api_view(["GET"])
def policies(_request):
    return Response({"items": [item.model_dump(mode="json") for item in service.policies()]})

@api_view(["POST"])
def inventory(request, case_id: str):
    try:
        value = service.inventory(case_id, request.data.get("policy_id", "policy.shareable.v1"))
    except (FileNotFoundError, KeyError) as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)
    return Response(value.model_dump(mode="json"))

@api_view(["POST"])
def preview(request, case_id: str):
    try:
        value = service.preview(case_id, request.data.get("policy_id", "policy.shareable.v1"))
    except (FileNotFoundError, KeyError, ValueError) as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    return Response(value.model_dump(mode="json"))

@api_view(["POST"])
def export(request, case_id: str):
    try:
        value = service.export(case_id, request.data.get("policy_id", "policy.shareable.v1"))
    except (FileNotFoundError, KeyError, ValueError) as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    return Response(value.model_dump(mode="json"), status=status.HTTP_201_CREATED)
