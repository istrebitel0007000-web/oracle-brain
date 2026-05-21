from apps.chat.models.conversation import Conversation, Message


def branch_conversation(
    conversation_id: int,
    user_id: int,
    branch_name: str,
    from_message_id: int,
) -> Conversation:
    """
    Create a branch of an existing conversation from a given message.
    Copies all messages up to and including from_message_id into the new branch.
    """
    parent = Conversation.objects.get(id=conversation_id, user_id=user_id)

    branch = Conversation.objects.create(
        user_id=user_id,
        title=f"{parent.title} [{branch_name}]",
        model=parent.model,
        persona=parent.persona,
        temperature=parent.temperature,
        response_length=parent.response_length,
        branch_name=branch_name,
        parent_conversation=parent,
    )

    messages_to_copy = parent.messages.filter(
        id__lte=from_message_id
    ).order_by("created_at")

    new_messages = [
        Message(
            conversation=branch,
            role=msg.role,
            content=msg.content,
            tokens_in=msg.tokens_in,
            tokens_out=msg.tokens_out,
            cost=msg.cost,
            model_used=msg.model_used,
        )
        for msg in messages_to_copy
    ]
    Message.objects.bulk_create(new_messages)

    return branch
