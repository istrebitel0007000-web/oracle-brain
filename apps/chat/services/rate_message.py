from apps.chat.models.conversation import Message


def rate_message(message_id: int, user_id: int, rating: int) -> Message:
    """Rate an assistant message 1-5. User must own the conversation."""
    msg = Message.objects.select_related("conversation").get(
        id=message_id,
        conversation__user_id=user_id,
        role=Message.Role.ASSISTANT,
    )
    msg.rating = max(1, min(5, rating))
    msg.save(update_fields=["rating", "updated_at"])
    return msg
