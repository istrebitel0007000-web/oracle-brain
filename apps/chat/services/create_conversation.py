from apps.chat.models.conversation import Conversation


def create_conversation(
    user_id: int,
    title: str = "New Conversation",
    model: str = "deepseek-r1-distill-llama-70b",
    persona: str = "tech_oracle",
    temperature: float = 0.7,
    response_length: str = "medium",
    is_incognito: bool = False,
) -> Conversation:
    """Create a new conversation for the given user."""
    return Conversation.objects.create(
        user_id=user_id,
        title=title,
        model=model,
        persona=persona,
        temperature=temperature,
        response_length=response_length,
        is_incognito=is_incognito,
    )
