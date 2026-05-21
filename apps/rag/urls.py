from django.urls import path
from apps.rag.views.rag import (
    ListRagChunksView, AddRagChunkView,
    SearchRagChunksView, DeleteRagChunkView,
)

urlpatterns = [
    path("list/", ListRagChunksView.as_view()),
    path("create/", AddRagChunkView.as_view()),
    path("search/", SearchRagChunksView.as_view()),
    path("<int:pk>/delete/", DeleteRagChunkView.as_view()),
]
