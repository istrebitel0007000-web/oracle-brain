from django.urls import path
from apps.notes.views.notes import (
    ListNotesView, CreateNoteView, UpdateNoteView,
    DeleteNoteView, PinNoteView,
)

urlpatterns = [
    path("list/", ListNotesView.as_view()),
    path("create/", CreateNoteView.as_view()),
    path("<int:pk>/update/", UpdateNoteView.as_view()),
    path("<int:pk>/delete/", DeleteNoteView.as_view()),
    path("<int:pk>/pin-toggle/", PinNoteView.as_view()),
]
