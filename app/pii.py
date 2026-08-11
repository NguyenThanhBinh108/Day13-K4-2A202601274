from __future__ import annotations

import hashlib
import re
from typing import Any

PII_PATTERNS: dict[str, str] = {
    "email": r"[\w\.-]+@[\w\.-]+\.\w+",
    "phone_vn": r"(?<!\d)(?:\+84|0)(?:[ .-]?\d){9}(?!\d)",
    "cccd": r"\b\d{12}\b",
    "credit_card": r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b",
    # Vietnamese passport: 1 letter + 7-8 digits (e.g. B1234567).
    "passport": r"\b[A-Za-z]\d{7,8}\b",
    # "Địa chỉ:"/"dia chi:" followed by free text up to the next separator.
    "address_vn": r"(?i)(?:địa chỉ|dia chi)\s*[:\-]?\s*[^\n,;]+",
}


def scrub_text(text: str) -> str:
    safe = text
    for name, pattern in PII_PATTERNS.items():
        safe = re.sub(pattern, f"[REDACTED_{name.upper()}]", safe)
    return safe


def scrub_value(value: Any) -> Any:
    """Recursively scrub PII from strings nested in dicts/lists/tuples.

    Used to sanitize an entire log record (not just a known `payload`/`event`
    key), because the validator scans the full JSON line for leaks — any
    field carrying free text (error detail, a future kwarg, ...) must be
    covered too.
    """
    if isinstance(value, str):
        return scrub_text(value)
    if isinstance(value, dict):
        return {key: scrub_value(v) for key, v in value.items()}
    if isinstance(value, (list, tuple)):
        return type(value)(scrub_value(v) for v in value)
    return value


def summarize_text(text: str, max_len: int = 80) -> str:
    safe = scrub_text(text).strip().replace("\n", " ")
    return safe[:max_len] + ("..." if len(safe) > max_len else "")


def hash_user_id(user_id: str) -> str:
    return hashlib.sha256(user_id.encode("utf-8")).hexdigest()[:12]
