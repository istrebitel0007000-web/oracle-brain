from django.db import models
from apps.core.models.base_model import BaseModel


class CostRecord(BaseModel):
    user = models.ForeignKey("auth.User", on_delete=models.CASCADE, related_name="cost_records")
    date = models.DateField(db_index=True)
    model = models.CharField(max_length=100)
    persona = models.CharField(max_length=100, blank=True)
    tokens_in = models.IntegerField(default=0)
    tokens_out = models.IntegerField(default=0)
    cost_usd = models.FloatField(default=0.0)

    class Meta:
        db_table = "cost_records"
        ordering = ["-date", "-created_at"]

    def __str__(self):
        return f"{self.date} {self.model}: ${self.cost_usd:.6f}"
