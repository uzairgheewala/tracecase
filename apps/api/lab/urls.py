from django.urls import path
from . import views
urlpatterns = [
    path("lab-bindings", views.bindings, name="lab-bindings"),
    path("lab-runs", views.run, name="lab-runs"),
    path("lab-comparisons", views.compare, name="lab-comparisons"),
    path("lab-runs/persist", views.persist, name="lab-persist"),
]
