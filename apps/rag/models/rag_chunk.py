from django.db import models
from apps.core.models.base_model import BaseModel


class RagChunk(BaseModel):
    user = models.ForeignKey("auth.User", on_delete=models.CASCADE, related_name="rag_chunks")
    text = models.TextField()
    source = models.CharField(max_length=500, blank=True)
    embedding = models.JSONField(default=list)
    tfidf_tokens = models.JSONField(default=list)

    class Meta:
        db_table = "rag_chunks"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.source or 'manual'}: {self.text[:60]}"
