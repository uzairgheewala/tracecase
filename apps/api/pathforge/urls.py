from django.urls import path
from . import views
urlpatterns=[path("pathforge-bindings",views.bindings,name="pathforge-bindings"),path("pathforge-runs",views.run,name="pathforge-run"),path("pathforge-comparisons",views.compare,name="pathforge-compare")]
