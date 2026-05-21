from django.db import models
from apps.core.models.base_model import BaseModel


class WebhookToken(BaseModel):
    user = models.ForeignKey("auth.User", on_delete=models.CASCADE, related_name="webhook_tokens")
    token = models.CharField(max_length=64, unique=True, db_index=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "webhook_tokens"

    def __str__(self):
        return f"{self.user_id}:{self.token[:8]}..."


class WebhookCall(BaseModel):
    token = models.CharField(max_length=255, db_index=True)
    prompt = models.TextField()
    response = models.TextField(blank=True)
    source_ip = models.GenericIPAddressField(null=True, blank=True)
    success = models.BooleanField(default=True)

    class Meta:
        db_table = "webhook_calls"
        ordering = ["-created_at"]

    def __str__(self):
        return f"webhook/{self.token[:8]} ({'ok' if self.success else 'fail'})"
