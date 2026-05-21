from django.db import models
from django.contrib.auth import get_user_model
from apps.core.models.base_model import BaseModel

User = get_user_model()


class Conversation(BaseModel):
    user = models.ForeignKey("auth.User", on_delete=models.CASCADE, related_name="conversations")
    title = models.CharField(max_length=255, default="New Conversation")
    model = models.CharField(max_length=100, default="deepseek-r1-distill-llama-70b")
    persona = models.CharField(max_length=100, default="tech_oracle")
    temperature = models.FloatField(default=0.7)
    response_length = models.CharField(max_length=20, default="medium")
    is_incognito = models.BooleanField(default=False)
    branch_name = models.CharField(max_length=100, default="main")
    parent_conversation = models.ForeignKey(
        "Conversation", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="branches"
    )

    class Meta:
        db_table = "conversations"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} - {self.title}"


class Message(BaseModel):
    class Role(models.TextChoices):
        USER = "user", "User"
        ASSISTANT = "assistant", "Assistant"
        SYSTEM = "system", "System"

    conversation = models.ForeignKey(
        "Conversation", on_delete=models.CASCADE, related_name="messages"
    )
    role = models.CharField(max_length=20, choices=Role.choices)
    content = models.TextField()
    tokens_in = models.IntegerField(default=0)
    tokens_out = models.IntegerField(default=0)
    cost = models.FloatField(default=0.0)
    model_used = models.CharField(max_length=100, blank=True)
    latency_ms = models.IntegerField(default=0)
    rating = models.IntegerField(null=True, blank=True)
    topic_tags = models.JSONField(default=list)
    is_bookmarked = models.BooleanField(default=False)

    class Meta:
        db_table = "messages"
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.role}: {self.content[:50]}"


class CacheEntry(BaseModel):
    cache_key = models.CharField(max_length=64, unique=True, db_index=True)
    response = models.TextField()
    persona = models.CharField(max_length=100)

    class Meta:
        db_table = "cache_entries"
