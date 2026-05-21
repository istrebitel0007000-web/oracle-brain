import re

_SECRET_PATTERNS = [
    (re.compile(r"\bgsk_[A-Za-z0-9_\-]{20,}\b"), "gsk_***REDACTED***"),
    (re.compile(r"\bsk-[A-Za-z0-9_\-]{20,}\b"), "sk-***REDACTED***"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "AKIA***REDACTED***"),
    (re.compile(r"\bASIA[0-9A-Z]{16}\b"), "ASIA***REDACTED***"),
    (re.compile(r"\bghp_[A-Za-z0-9_\-]{20,}\b"), "ghp_***REDACTED***"),
    (re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}\b"), "xox?-***REDACTED***"),
    (re.compile(r"\bAIza[A-Za-z0-9_\-]{35}\b"), "AIza***REDACTED***"),
    (re.compile(r"\b[0-9]{9,12}:[A-Za-z0-9_\-]{30,}\b"), "***TELEGRAM_TOKEN_REDACTED***"),
    (re.compile(r"(?i)\b(Bearer|Token)\s+[A-Za-z0-9._\-]{20,}\b"), "\\1 ***REDACTED***"),
    (re.compile(
        r"(?i)\b([A-Z][A-Z0-9_]{1,30}_(?:KEY|TOKEN|SECRET|PASSWORD|PASS))\s*[:=]\s*['\"]?([^\s'\"]{6,})['\"]?"
    ), r"\1=***REDACTED***"),
    (re.compile(
        r"(?i)\b(api[_\-]?key|secret|password|passwd|pwd)\s*[:=]\s*['\"]?([^\s'\"]{6,})['\"]?"
    ), r"\1=***REDACTED***"),
    (re.compile(
        r"\beyJ[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\b"
    ), "***JWT_REDACTED***"),
    (re.compile(
        r"-----BEGIN (RSA |EC |DSA |OPENSSH |)PRIVATE KEY-----[\s\S]*?-----END \1PRIVATE KEY-----"
    ), "-----BEGIN \\1PRIVATE KEY----- ***REDACTED*** -----END \\1PRIVATE KEY-----"),
]


def redact_secrets(text: str) -> str:
    """Substitute likely secrets with REDACTED markers. Idempotent."""
    if not text:
        return text
    out = text
    for rx, repl in _SECRET_PATTERNS:
        out = rx.sub(repl, out)
    return out


def contains_secret(text: str) -> bool:
    """Quick yes/no check for secrets in text."""
    if not text:
        return False
    for rx, _ in _SECRET_PATTERNS:
        if rx.search(text):
            return True
    return False


def scan_secrets(text: str) -> list:
    """Return list of detected secret pattern names found in text."""
    found = []
    pattern_names = [
        "Groq API Key", "OpenAI API Key", "AWS Access Key", "AWS Session Key",
        "GitHub Token", "Slack Token", "Google API Key", "Telegram Token",
        "Bearer Token", "Env Variable Secret", "Generic Secret",
        "JWT Token", "Private Key",
    ]
    for i, (rx, _) in enumerate(_SECRET_PATTERNS):
        if rx.search(text):
            name = pattern_names[i] if i < len(pattern_names) else f"Pattern {i}"
            found.append(name)
    return found
