import time
import urllib.request
import urllib.parse
import json
import logging
from apps.agent.models.agent_tool_call import AgentToolCall

log = logging.getLogger("oracle.agent")

_TOOLS_REGISTRY: dict[str, callable] = {}


def register_tool(name: str):
    """Decorator to register an agent tool function."""
    def decorator(fn):
        _TOOLS_REGISTRY[name] = fn
        return fn
    return decorator


def list_tools() -> list[dict]:
    """Return all registered tool names and docstrings."""
    return [
        {"name": name, "description": (fn.__doc__ or "").strip()}
        for name, fn in _TOOLS_REGISTRY.items()
    ]


def run_tool(
    tool_name: str,
    tool_input: dict,
    user_id: int,
    conversation_id: int = None,
) -> str:
    """
    Execute a named tool and record the call in the database.
    Returns the tool output as a string.
    """
    if tool_name not in _TOOLS_REGISTRY:
        return f"[Tool Error] Unknown tool: {tool_name}"

    start = time.time()
    success = True
    output = ""

    try:
        output = _TOOLS_REGISTRY[tool_name](**tool_input)
        output = str(output)
    except Exception as e:
        output = f"[Tool Error] {tool_name}: {e}"
        success = False
        log.exception(f"Agent tool {tool_name} failed: {e}")

    latency_ms = int((time.time() - start) * 1000)

    AgentToolCall.objects.create(
        user_id=user_id,
        conversation_id=conversation_id,
        tool_name=tool_name,
        tool_input=tool_input,
        tool_output=output,
        success=success,
        latency_ms=latency_ms,
    )

    return output


# ──────────────────────────────────────────────
# Built-in Tools
# ──────────────────────────────────────────────

@register_tool("web_fetch")
def _tool_web_fetch(url: str, max_chars: int = 3000) -> str:
    """Fetch the text content of a web page."""
    _validate_url(url)
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "OracleBrain/5.5 (+https://github.com/istrebitel0007000-web/oracle-brain)"},
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        raw = resp.read(max_chars * 4).decode("utf-8", errors="replace")
    return _strip_html(raw)[:max_chars]


@register_tool("web_search")
def _tool_web_search(query: str, num_results: int = 5) -> str:
    """Search the web using DuckDuckGo Lite and return top results."""
    encoded = urllib.parse.quote_plus(query)
    url = f"https://duckduckgo.com/lite?q={encoded}&kl=us-en"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "OracleBrain/5.5"},
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        html = resp.read(50000).decode("utf-8", errors="replace")
    return _strip_html(html)[:4000]


@register_tool("calculator")
def _tool_calculator(expression: str) -> str:
    """Evaluate a safe mathematical expression and return the result."""
    import ast
    import operator

    allowed_ops = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
        ast.UAdd: operator.pos,
        ast.Mod: operator.mod,
        ast.FloorDiv: operator.floordiv,
    }

    def _eval(node):
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.BinOp):
            return allowed_ops[type(node.op)](_eval(node.left), _eval(node.right))
        if isinstance(node, ast.UnaryOp):
            return allowed_ops[type(node.op)](_eval(node.operand))
        raise ValueError(f"Unsupported node: {type(node)}")

    tree = ast.parse(expression.strip(), mode="eval")
    result = _eval(tree.body)
    return str(result)


@register_tool("get_time")
def _tool_get_time(timezone_name: str = "UTC") -> str:
    """Return the current date and time in the given timezone."""
    from datetime import datetime, timezone as tz
    import zoneinfo
    try:
        zone = zoneinfo.ZoneInfo(timezone_name)
        now = datetime.now(zone)
    except Exception:
        now = datetime.now(tz.utc)
    return now.strftime("%Y-%m-%d %H:%M:%S %Z")


@register_tool("read_file")
def _tool_read_file(path: str, max_chars: int = 5000) -> str:
    """Read a local file and return its content (safe paths only)."""
    import os
    safe_root = "/tmp/oracle_agent_files"
    os.makedirs(safe_root, exist_ok=True)
    real_path = os.path.realpath(os.path.join(safe_root, path))
    if not real_path.startswith(safe_root):
        raise PermissionError("Path traversal attempt blocked")
    with open(real_path, "r", encoding="utf-8", errors="replace") as f:
        return f.read(max_chars)


@register_tool("write_file")
def _tool_write_file(path: str, content: str) -> str:
    """Write content to a local file (safe paths only)."""
    import os
    safe_root = "/tmp/oracle_agent_files"
    os.makedirs(safe_root, exist_ok=True)
    real_path = os.path.realpath(os.path.join(safe_root, path))
    if not real_path.startswith(safe_root):
        raise PermissionError("Path traversal attempt blocked")
    with open(real_path, "w", encoding="utf-8") as f:
        f.write(content)
    return f"Written {len(content)} characters to {path}"


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def _validate_url(url: str) -> None:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("Only http/https URLs are allowed")
    blocked_hosts = {"localhost", "127.0.0.1", "0.0.0.0", "::1"}
    if parsed.hostname in blocked_hosts:
        raise ValueError("Local/internal URLs are not allowed")


def _strip_html(html: str) -> str:
    import re
    text = re.sub(r"<script[^>]*>[\s\S]*?</script>", "", html, flags=re.IGNORECASE)
    text = re.sub(r"<style[^>]*>[\s\S]*?</style>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"&lt;", "<", text)
    text = re.sub(r"&gt;", ">", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()
