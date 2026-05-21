from django.urls import path
from apps.costs.views.costs import ListCostsView, CostSummaryView

urlpatterns = [
    path("list/", ListCostsView.as_view()),
    path("summary/", CostSummaryView.as_view()),
]
