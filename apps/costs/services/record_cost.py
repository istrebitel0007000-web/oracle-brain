from django.utils import timezone
from apps.costs.models.cost_record import CostRecord


def record_cost(
    user_id: int,
    model: str,
    persona: str,
    tokens_in: int,
    tokens_out: int,
    cost_usd: float,
) -> CostRecord:
    """Record a cost entry for a single AI call."""
    return CostRecord.objects.create(
        user_id=user_id,
        date=timezone.now().date(),
        model=model,
        persona=persona,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        cost_usd=cost_usd,
    )
