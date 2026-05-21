from apps.chat.models.conversation import Conversation


def delete_conversation(conversation_id: int, user_id: int) -> None:
    """Delete a conversation and all its messages."""
    Conversation.objects.filter(id=conversation_id, user_id=user_id).delete()
