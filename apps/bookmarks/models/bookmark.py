from django.db import models
from apps.core.models.base_model import BaseModel


class Bookmark(BaseModel):
    user = models.ForeignKey("auth.User", on_delete=models.CASCADE, related_name="bookmarks")
    label = models.CharField(max_length=255)
    content = models.TextField()
    message = models.ForeignKey(
        "chat.Message", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="bookmarks"
    )

    class Meta:
        db_table = "bookmarks"
        ordering = ["-created_at"]

    def __str__(self):
        return self.label
