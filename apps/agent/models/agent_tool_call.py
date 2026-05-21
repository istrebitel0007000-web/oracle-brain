from django.db import models
from apps.core.models.base_model import BaseModel


class AgentToolCall(BaseModel):
    user = models.ForeignKey("auth.User", on_delete=models.CASCADE, related_name="agent_tool_calls")
    conversation = models.ForeignKey(
        "chat.Conversation", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="agent_tool_calls"
    )
    tool_name = models.CharField(max_length=100)
    tool_input = models.JSONField(default=dict)
    tool_output = models.TextField(blank=True)
    success = models.BooleanField(default=True)
    latency_ms = models.IntegerField(default=0)

    class Meta:
        db_table = "agent_tool_calls"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.tool_name} ({'ok' if self.success else 'fail'})"
