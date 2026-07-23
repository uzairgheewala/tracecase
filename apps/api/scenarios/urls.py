from django.urls import path

from . import views

urlpatterns = [
    path("scenario-families", views.family_list, name="scenario-family-list"),
    path("scenario-families/<str:family_id>", views.family_detail, name="scenario-family-detail"),
    path("scenario-generate", views.generate, name="scenario-generate"),
]
