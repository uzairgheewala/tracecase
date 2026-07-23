from django.urls import include, path
from django.http import JsonResponse


def health(_request):
    return JsonResponse({"status": "ok", "service": "tracecase-api", "milestone": "A"})


urlpatterns = [
    path("api/health", health),
    path("api/", include("cases.urls")),
]
