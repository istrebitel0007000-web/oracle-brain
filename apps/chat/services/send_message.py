import time
import logging
from django.conf import settings
from apps.chat.models.conversation import Conversation, Message, CacheEntry
from apps.core.services.groq_client import ask_groq
from apps.costs.services.record_cost import record_cost
from apps.rag.services.search_chunks import search_chunks
from apps.personas.services.get_persona import get_persona

log = logging.getLogger("oracle.chat")

_SYSTEM_BASE = """You are Oracle Brain — a powerful, thoughtful AI assistant.
Be concise, accurate, and helpful. Adapt your tone to the persona assigned."""


def _build_system_prompt(persona_key: str, rag_context: str = "") -> str:
    persona = get_persona(persona_key)
    instruction = persona.instruction if persona else _SYSTEM_BASE
    if rag_context:
        instruction += f"\n\n[Relevant context from knowledge base]\n{rag_context}"
    return instruction


def _build_messages(conversation: Conversation, user_content: str) -> list:
    cfg = settings.ORACLE_CONFIG
    limit = cfg["max_history_turns"] * 2
    total = conversation.messages.count()
    offset = max(0, total - limit)
    history = conversation.messages.order_by("created_at")[offset:]
    messages = []
    for msg in history:
        messages.append({"role": msg.role, "content": msg.content})
    messages.append({"role": "user", "content": user_content})
    return messages


def _get_cache(key: str, persona: str) -> object:
    try:
        entry = CacheEntry.objects.get(cache_key=key, persona=persona)
        return entry.response
    except CacheEntry.DoesNotExist:
        return None


def _set_cache(key: str, persona: str, response: str) -> None:
    CacheEntry.objects.update_or_create(
        cache_key=key,
        defaults={"persona": persona, "response": response},
    )


def send_message(
    conversation_id: int,
    user_id: int,
    content: str,
    on_token=None,
) -> Message:
    """
    Core send message service.
    Saves user message, calls Groq, saves assistant reply,
    records cost, returns assistant Message instance.
    """
    import hashlib

    conversation = Conversation.objects.get(id=conversation_id, user_id=user_id)

    # Save user message
    user_msg = Message.objects.create(
        conversation=conversation,
        role=Message.Role.USER,
        content=content,
    )

    # RAG context injection
    rag_context = ""
    try:
        chunks = search_chunks(user_id=user_id, query=content, top_k=3)
        if chunks:
            rag_context = "\n\n".join(c.text for c in chunks)
    except Exception as e:
        log.warning(f"RAG search failed: {e}")

    # System prompt
    system_prompt = _build_system_prompt(conversation.persona, rag_context)

    # Cache check
    cache_key = hashlib.sha256(
        f"{conversation.persona}:{content}".encode()
    ).hexdigest()[:32]

    if not on_token:
        cached = _get_cache(cache_key, conversation.persona)
        if cached:
            assistant_msg = Message.objects.create(
                conversation=conversation,
                role=Message.Role.ASSISTANT,
                content=cached,
                model_used="cache",
            )
            return assistant_msg

    # Build messages for API
    api_messages = [{"role": "system", "content": system_prompt}]
    api_messages += _build_messages(conversation, content)

    # Truncate to max prompt length
    cfg = settings.ORACLE_CONFIG
    max_len = cfg["max_prompt_len"]
    total_len = sum(len(m["content"]) for m in api_messages)
    while total_len > max_len and len(api_messages) > 2:
        removed = api_messages.pop(1)
        total_len -= len(removed["content"])

    # Call Groq
    start = time.time()
    result = ask_groq(
        messages=api_messages,
        model=conversation.model,
        temperature=conversation.temperature,
        on_token=on_token,
    )
    latency_ms = int((time.time() - start) * 1000)

    reply = result["content"]

    # Save assistant message
    assistant_msg = Message.objects.create(
        conversation=conversation,
        role=Message.Role.ASSISTANT,
        content=reply,
        tokens_in=result["tokens_in"],
        tokens_out=result["tokens_out"],
        cost=result["cost"],
        model_used=result["model"],
        latency_ms=latency_ms,
    )

    # Cache successful response
    if result["model"] != "offline" and not on_token:
        _set_cache(cache_key, conversation.persona, reply)

    # Record cost
    try:
        record_cost(
            user_id=user_id,
            model=result["model"],
            persona=conversation.persona,
            tokens_in=result["tokens_in"],
            tokens_out=result["tokens_out"],
            cost_usd=result["cost"],
        )
    except Exception as e:
        log.warning(f"Cost recording failed: {e}")

    return assistant_msg
