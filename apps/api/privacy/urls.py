from django.urls import path
from . import views
urlpatterns = [
    path("privacy-policies", views.policies, name="privacy-policies"),
    path("cases/<str:case_id>/privacy-inventory", views.inventory, name="privacy-inventory"),
    path("cases/<str:case_id>/redaction-preview", views.preview, name="redaction-preview"),
    path("cases/<str:case_id>/shareable-export", views.export, name="shareable-export"),
]
