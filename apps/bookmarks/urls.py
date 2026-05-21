from django.urls import path
from apps.bookmarks.views.bookmarks import (
    ListBookmarksView, CreateBookmarkView,
    UpdateBookmarkView, DeleteBookmarkView,
)

urlpatterns = [
    path("list/", ListBookmarksView.as_view()),
    path("create/", CreateBookmarkView.as_view()),
    path("<int:pk>/update/", UpdateBookmarkView.as_view()),
    path("<int:pk>/delete/", DeleteBookmarkView.as_view()),
]
