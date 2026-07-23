from django.urls import path

from . import views

urlpatterns = [
    path("comparisons", views.compare_cases, name="comparison-create"),
]
