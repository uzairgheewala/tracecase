from django.urls import path
from . import views
urlpatterns=[path("cases/<str:case_id>/health",views.case_health,name="case-health"),path("cases/<str:case_id>/neighborhood",views.case_neighborhood,name="case-neighborhood")]
