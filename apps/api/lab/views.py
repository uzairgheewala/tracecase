from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from pydantic import ValidationError
from .services import LabService

service = LabService()

@api_view(["GET"])
def bindings(_request):
    return Response({"items": [item.model_dump(mode="json") for item in service.bindings()]})

@api_view(["POST"])
def run(request):
    try:
        value = service.run(dict(request.data))
    except (ValidationError, ValueError, RuntimeError) as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    return Response(value.model_dump(mode="json"))

@api_view(["POST"])
def compare(request):
    try:
        value = service.compare(dict(request.data))
    except (ValidationError, ValueError, RuntimeError) as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    return Response(value.model_dump(mode="json"))

@api_view(["POST"])
def persist(request):
    try:
        value, path, archive = service.persist(dict(request.data))
    except (ValidationError, ValueError, RuntimeError) as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    return Response({"receipt": value.receipt.model_dump(mode="json"), "bundle_path": str(path), "archive_path": str(archive)}, status=status.HTTP_201_CREATED)
