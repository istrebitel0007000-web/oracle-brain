from django.urls import path
from apps.personas.views.personas import (
    ListPersonasView, CreatePersonaView,
    UpdatePersonaView, DeletePersonaView,
)

urlpatterns = [
    path("list/", ListPersonasView.as_view()),
    path("create/", CreatePersonaView.as_view()),
    path("<int:pk>/update/", UpdatePersonaView.as_view()),
    path("<int:pk>/delete/", DeletePersonaView.as_view()),
]
