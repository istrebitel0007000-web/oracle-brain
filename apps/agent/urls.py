from django.urls import path
from apps.agent.views.agent import ListToolsView, RunToolView

urlpatterns = [
    path("tools/list/", ListToolsView.as_view()),
    path("tools/run/", RunToolView.as_view()),
]
