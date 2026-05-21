from django.db import models
from apps.core.models.base_model import BaseModel


class Persona(BaseModel):
    class PersonaType(models.TextChoices):
        BUILTIN = "builtin", "Built-in"
        CUSTOM = "custom", "Custom"

    key = models.CharField(max_length=100, unique=True, db_index=True)
    name = models.CharField(max_length=255)
    instruction = models.TextField()
    temperature = models.FloatField(default=0.7)
    length = models.CharField(max_length=20, default="medium")
    persona_type = models.CharField(
        max_length=20,
        choices=PersonaType.choices,
        default=PersonaType.CUSTOM,
    )

    class Meta:
        db_table = "personas"
        ordering = ["name"]

    def __str__(self):
        return self.name
