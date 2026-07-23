from django.urls import include, path
from django.http import JsonResponse


def health(_request):
    return JsonResponse({"status": "ok", "service": "tracecase-api", "milestone": "D"})


urlpatterns = [
    path("api/health", health),
    path("api/", include("cases.urls")),
    path("api/", include("scenarios.urls")),
    path("api/", include("comparisons.urls")),
    path("api/", include("privacy.urls")),
    path("api/", include("lab.urls")),
]
