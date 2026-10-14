"""Logging helpers with secret redaction."""

from __future__ import annotations

import logging
import re

_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_\-]{8,}"),
    re.compile(r"(?i)(api[_-]?key|authorization|bearer|token)(\s*[=:]\s*|\s+)[^\s,;]+"),
]


def redact(text: str) -> str:
    """Mask API-key-like substrings in text."""
    out = _PATTERNS[0].sub("[REDACTED]", text)
    return _PATTERNS[1].sub(lambda m: f"{m.group(1)}{m.group(2)}[REDACTED]", out)


class RedactingFilter(logging.Filter):
    """Redact secrets from log messages before they are emitted."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = redact(record.getMessage())
        record.args = ()
        return True


def get_logger(name: str) -> logging.Logger:
    """Return a logger with the redacting filter attached once."""
    logger = logging.getLogger(name)
    if not any(isinstance(f, RedactingFilter) for f in logger.filters):
        logger.addFilter(RedactingFilter())
    return logger
