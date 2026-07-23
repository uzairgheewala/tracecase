from django.urls import path

from . import views

urlpatterns = [
    path("cases", views.case_list, name="case-list"),
    path("cases/<str:case_id>", views.case_detail, name="case-detail"),
    path("cases/<str:case_id>/graph", views.case_graph, name="case-graph"),
    path("cases/<str:case_id>/assembled-graph", views.case_assembled_graph, name="case-assembled-graph"),
    path("cases/<str:case_id>/timeline", views.case_timeline, name="case-timeline"),
    path("cases/<str:case_id>/validation", views.case_validation, name="case-validation"),
    path("cases/<str:case_id>/invariants", views.case_invariants, name="case-invariants"),
    path("cases/<str:case_id>/analysis", views.case_analysis, name="case-analysis"),
]
