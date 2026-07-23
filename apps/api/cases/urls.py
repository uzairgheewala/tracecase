from django.urls import path

from . import views

urlpatterns = [
    path("cases", views.case_list, name="case-list"),
    path("cases/<str:case_id>", views.case_detail, name="case-detail"),
    path("cases/<str:case_id>/graph", views.case_graph, name="case-graph"),
    path("cases/<str:case_id>/validation", views.case_validation, name="case-validation"),
]
