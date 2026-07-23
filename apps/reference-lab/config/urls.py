from django.urls import include, path
from django.http import JsonResponse

urlpatterns = [
    path("health", lambda _request: JsonResponse({"status": "ok", "service": "tracecase-reference-lab"})),
    path("api/", include("workflow.urls")),
]
