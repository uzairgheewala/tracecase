from django.urls import path
from . import views
urlpatterns = [
    path("imports", views.import_transcript, name="lab-import"),
    path("imports/<int:import_run_id>", views.import_status, name="lab-import-status"),
]
