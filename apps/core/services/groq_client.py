import random
import time
import logging
from typing import Optional, Callable
from django.conf import settings

log = logging.getLogger("oracle.core")

_PRICING_PER_1M = {
    "deepseek-r1-distill-llama-70b": {"in": 0.75, "out": 0.99},
    "qwen-2.5-72b-instruct": {"in": 0.59, "out": 0.79},
    "llama-3.3-70b-versatile": {"in": 0.59, "out": 0.79},
    "llama-3.1-8b-instant": {"in": 0.05, "out": 0.08},
    "gemma2-9b-it": {"in": 0.20, "out": 0.20},
    "meta-llama/llama-4-scout-17b-16e-instruct": {"in": 0.11, "out": 0.34},
}


def get_groq_client(api_key: str):
    """Return a Groq client for the given api_key."""
    from groq import Groq
    return Groq(api_key=api_key)


def get_random_api_key() -> Optional[str]:
    """Return a random API key from the configured list."""
    keys = settings.GROQ_API_KEYS
    if not keys:
        return None
    return random.choice(keys)


def calculate_cost(model: str, tokens_in: int, tokens_out: int) -> float:
    """Calculate USD cost for a given model and token counts."""
    pricing = _PRICING_PER_1M.get(model, {"in": 0.59, "out": 0.79})
    cost = (tokens_in / 1_000_000) * pricing["in"]
    cost += (tokens_out / 1_000_000) * pricing["out"]
    return round(cost, 8)


def ask_groq(
    messages: list,
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    on_token: Optional[Callable] = None,
) -> dict:
    """
    Core Groq API call with:
    - Multi-key rotation
    - Multi-model fallback
    - Retry with Retry-After header respect
    - Streaming support via on_token callback
    - Ollama fallback when Groq fails

    Returns dict with keys: content, model, tokens_in, tokens_out, cost
    """
    cfg = settings.ORACLE_CONFIG
    model = model or cfg["model"]
    temperature = temperature if temperature is not None else cfg["temperature"]
    max_tokens = max_tokens or cfg["max_tokens"]
    max_retries = cfg["max_retries"]
    request_delay = cfg["request_delay"]

    models_to_try = [model] + [
        m for m in cfg["fallback_models"] if m != model
    ]

    last_error = None

    for current_model in models_to_try:
        for attempt in range(max_retries):
            api_key = get_random_api_key()
            if not api_key:
                return _ollama_fallback(messages, cfg)

            try:
                client = get_groq_client(api_key)
                time.sleep(request_delay)

                if on_token:
                    return _stream_groq(
                        client, messages, current_model,
                        temperature, max_tokens, on_token
                    )

                response = client.chat.completions.create(
                    model=current_model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )

                content = response.choices[0].message.content or ""
                tokens_in = getattr(response.usage, "prompt_tokens", 0)
                tokens_out = getattr(response.usage, "completion_tokens", 0)
                cost = calculate_cost(current_model, tokens_in, tokens_out)

                return {
                    "content": content,
                    "model": current_model,
                    "tokens_in": tokens_in,
                    "tokens_out": tokens_out,
                    "cost": cost,
                }

            except Exception as e:
                last_error = e
                err_str = str(e).lower()

                # Respect Retry-After header
                retry_after = _parse_retry_after(str(e))
                if retry_after:
                    log.warning(f"Rate limited. Waiting {retry_after}s...")
                    time.sleep(retry_after)
                    continue

                if "rate_limit" in err_str or "429" in err_str:
                    wait = (attempt + 1) * 2
                    log.warning(f"Rate limit on {current_model}, waiting {wait}s")
                    time.sleep(wait)
                    continue

                if "model_not_found" in err_str or "404" in err_str:
                    log.warning(f"Model {current_model} not found, trying next")
                    break

                log.exception(f"Groq error on {current_model} attempt {attempt}: {e}")
                break

    # All Groq keys/models failed — try Ollama
    if cfg.get("ollama_enabled"):
        return _ollama_fallback(messages, cfg)

    return {
        "content": f"[Oracle Brain] All AI models are currently unavailable. Last error: {last_error}",
        "model": "offline",
        "tokens_in": 0,
        "tokens_out": 0,
        "cost": 0.0,
    }


def _stream_groq(
    client,
    messages: list,
    model: str,
    temperature: float,
    max_tokens: int,
    on_token: Callable,
) -> dict:
    """Handle Groq streaming response."""
    stream = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        stream=True,
    )

    full_content = ""
    tokens_in = 0
    tokens_out = 0

    for chunk in stream:
        delta = chunk.choices[0].delta
        if delta and delta.content:
            full_content += delta.content
            on_token(delta.content)
        if hasattr(chunk, "usage") and chunk.usage:
            tokens_in = getattr(chunk.usage, "prompt_tokens", 0)
            tokens_out = getattr(chunk.usage, "completion_tokens", 0)

    cost = calculate_cost(model, tokens_in, tokens_out)
    return {
        "content": full_content,
        "model": model,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "cost": cost,
    }


def _ollama_fallback(messages: list, cfg: dict) -> dict:
    """Fallback to local Ollama when Groq is unavailable."""
    import urllib.request
    import json

    url = f"{cfg['ollama_url']}/api/chat"
    payload = json.dumps({
        "model": cfg["ollama_model"],
        "messages": messages,
        "stream": False,
    }).encode()

    try:
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
            content = data.get("message", {}).get("content", "")
            return {
                "content": content,
                "model": f"ollama/{cfg['ollama_model']}",
                "tokens_in": 0,
                "tokens_out": 0,
                "cost": 0.0,
            }
    except Exception as e:
        log.exception(f"Ollama fallback failed: {e}")
        return {
            "content": "[Oracle Brain] All AI services are currently unavailable.",
            "model": "offline",
            "tokens_in": 0,
            "tokens_out": 0,
            "cost": 0.0,
        }


def _parse_retry_after(error_str: str) -> object:
    """Parse retry-after seconds from Groq error message."""
    import re
    match = re.search(r"retry.after[:\s]+(\d+)", error_str, re.IGNORECASE)
    if match:
        return int(match.group(1))
    match = re.search(r"x-ratelimit-reset[:\s]+(\d+)", error_str, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None
