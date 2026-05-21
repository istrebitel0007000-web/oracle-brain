import json
import csv
import io
from apps.chat.models.conversation import Conversation
from apps.core.services.redact_secrets import redact_secrets


def export_conversation(
    conversation_id: int,
    user_id: int,
    fmt: str = "json",
) -> tuple[str, str]:
    """
    Export a conversation in the requested format.
    Returns (content_string, content_type).
    Secrets are automatically redacted from exported content.
    Supported formats: json, markdown, csv, txt
    """
    conversation = Conversation.objects.prefetch_related("messages").get(
        id=conversation_id, user_id=user_id
    )
    messages = list(conversation.messages.order_by("created_at"))

    if fmt == "json":
        data = {
            "title": conversation.title,
            "model": conversation.model,
            "persona": conversation.persona,
            "created_at": conversation.created_at.isoformat(),
            "messages": [
                {
                    "role": msg.role,
                    "content": redact_secrets(msg.content),
                    "created_at": msg.created_at.isoformat(),
                }
                for msg in messages
            ],
        }
        return json.dumps(data, indent=2, ensure_ascii=False), "application/json"

    if fmt == "markdown":
        lines = [f"# {conversation.title}\n"]
        lines.append(f"**Model:** {conversation.model}  ")
        lines.append(f"**Persona:** {conversation.persona}\n")
        for msg in messages:
            role_label = "**You**" if msg.role == "user" else "**Oracle Brain**"
            lines.append(f"\n{role_label}:\n{redact_secrets(msg.content)}\n")
        return "\n".join(lines), "text/markdown"

    if fmt == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["role", "content", "created_at"])
        for msg in messages:
            writer.writerow([msg.role, redact_secrets(msg.content), msg.created_at.isoformat()])
        return output.getvalue(), "text/csv"

    # txt default
    lines = [f"Conversation: {conversation.title}\n"]
    for msg in messages:
        prefix = "You" if msg.role == "user" else "Oracle Brain"
        lines.append(f"{prefix}: {redact_secrets(msg.content)}\n")
    return "\n".join(lines), "text/plain"
