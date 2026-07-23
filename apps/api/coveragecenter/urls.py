from django.urls import path
from . import views
urlpatterns=[path("coverage",views.coverage_report,name="coverage-report")]
