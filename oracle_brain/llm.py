"""
oracle_brain/llm.py — LLM: Groq (key rotation) + Anthropic Claude fallback
BUG #4 FIX: fail-fast in production when no API keys found
BUG #13 FIX: image_path typed as Optional[str]
"""
from __future__ import annotations
import hashlib, logging, os, sys, threading, time
from typing import Any, Generator, Optional

log = logging.getLogger("oracle.llm")

try:
    from groq import Groq
    _GROQ_AVAILABLE = True
except ImportError:
    _GROQ_AVAILABLE = False

try:
    import anthropic as _anthropic_lib
    _ANTHROPIC_AVAILABLE = True
except ImportError:
    _ANTHROPIC_AVAILABLE = False


def _load_groq_keys() -> list[str]:
    keys = []
    for i in range(1, 11):
        k = os.getenv(f"GROQ_KEY_{i}", "").strip()
        if k and k != "MISSING_KEY":
            keys.append(k)
    if not keys:
        env_key = os.getenv("GROQ_API_KEY", "").strip()
        if env_key and env_key != "MISSING_KEY":
            keys.append(env_key)
    if not keys:
        env = os.getenv("FLASK_ENV", "development")
        if env == "production":
            raise RuntimeError(
                "No Groq API keys found. Set GROQ_KEY_1 in your Render environment variables."
            )
        log.warning("WARNING: No Groq API keys. Set GROQ_KEY_1 in .env")
        keys = ["MISSING_KEY"]
    return keys


_groq_keys: list[str] = []
_key_index: int = 0
_key_lock = threading.Lock()
_groq_clients: list[Any] = []
_ask_lock = threading.Lock()

_response_cache: dict[str, tuple[str, float]] = {}
_cache_lock = threading.Lock()
CACHE_TTL = 300


def init_llm() -> None:
    global _groq_keys, _groq_clients
    _groq_keys = _load_groq_keys()
    if _GROQ_AVAILABLE:
        _groq_clients = [Groq(api_key=k) for k in _groq_keys if k != "MISSING_KEY"]
    log.info(f"LLM init: {len(_groq_clients)} Groq client(s), Anthropic={'yes' if _ANTHROPIC_AVAILABLE else 'no'}")


def _next_client() -> Optional[Any]:
    global _key_index
    if not _groq_clients:
        return None
    with _key_lock:
        client = _groq_clients[_key_index % len(_groq_clients)]
        _key_index = (_key_index + 1) % len(_groq_clients)
    return client


def _cache_key(prompt: str, model: str, image_path: Optional[str] = None) -> str:
    raw = f"{model}::{prompt}::{image_path or ''}"
    return hashlib.sha256(raw.encode()).hexdigest()


def _get_cached(key: str) -> Optional[str]:
    with _cache_lock:
        entry = _response_cache.get(key)
        if entry:
            text, ts = entry
            if time.time() - ts < CACHE_TTL:
                return text
            del _response_cache[key]
    return None


def _set_cache(key: str, value: str) -> None:
    with _cache_lock:
        _response_cache[key] = (value, time.time())
        if len(_response_cache) > 500:
            now = time.time()
            stale = [k for k, (_, ts) in _response_cache.items() if now - ts > CACHE_TTL]
            for k in stale:
                del _response_cache[k]


def _ask_anthropic(messages: list[dict], model: str, max_tokens: int,
                   temperature: float, system: str = "", stream: bool = False):
    if not _ANTHROPIC_AVAILABLE:
        raise RuntimeError("anthropic package not installed.")
    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set.")
    client = _anthropic_lib.Anthropic(api_key=api_key)
    kwargs: dict[str, Any] = {"model": model, "max_tokens": max_tokens, "messages": messages}
    if system:
        kwargs["system"] = system
    if stream:
        def _gen():
            with client.messages.stream(**kwargs) as s:
                for text in s.text_stream:
                    yield text
        return _gen()
    resp = client.messages.create(**kwargs)
    return resp.content[0].text


def ask_llm_stream(messages: list[dict], model: str, fallback_models: list[str],
                   anthropic_model: str, anthropic_fallback_enabled: bool,
                   max_tokens: int = 4096, temperature: float = 0.7,
                   system: str = "", request_delay: float = 0.3,
                   max_retries: int = 5) -> Generator[str, None, None]:
    models_to_try = [model] + [m for m in fallback_models if m != model]
    for attempt_model in models_to_try:
        for attempt in range(max_retries):
            client = _next_client()
            if client is None:
                break
            try:
                if attempt > 0:
                    time.sleep(request_delay)
                response = client.chat.completions.create(
                    model=attempt_model, messages=messages,
                    max_tokens=max_tokens, temperature=temperature, stream=True,
                )
                for chunk in response:
                    delta = chunk.choices[0].delta
                    if delta and delta.content:
                        yield delta.content
                return
            except Exception as e:
                err = str(e).lower()
                if "rate_limit" in err or "429" in err:
                    continue
                if "model" in err and "not found" in err:
                    break
                log.warning(f"Stream error attempt {attempt}: {e}")

    if anthropic_fallback_enabled and _ANTHROPIC_AVAILABLE and os.getenv("ANTHROPIC_API_KEY"):
        try:
            clean_msgs = [m for m in messages if m["role"] != "system"]
            gen = _ask_anthropic(clean_msgs, anthropic_model, max_tokens, temperature, system, stream=True)
            if hasattr(gen, "__iter__"):
                for chunk in gen:
                    yield chunk
            return
        except Exception as e:
            log.error(f"Anthropic stream fallback failed: {e}")

    yield "[Error: All LLM providers failed. Please try again later.]"


def clear_cache() -> int:
    with _cache_lock:
        count = len(_response_cache)
        _response_cache.clear()
    return count
