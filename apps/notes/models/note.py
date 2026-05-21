from django.db import models
from apps.core.models.base_model import BaseModel


class Note(BaseModel):
    user = models.ForeignKey("auth.User", on_delete=models.CASCADE, related_name="notes")
    text = models.TextField()
    is_pinned = models.BooleanField(default=False, db_index=True)

    class Meta:
        db_table = "notes"
        ordering = ["-is_pinned", "-created_at"]

    def __str__(self):
        return self.text[:80]
