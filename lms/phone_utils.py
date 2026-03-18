"""WhatsApp / phone normalization for lead capture."""
from __future__ import annotations

import re


def normalize_whatsapp_digits(raw: str) -> str:
    """Strip to digits only."""
    return re.sub(r"\D", "", (raw or "").strip())


def validate_whatsapp_number(raw: str) -> tuple[str | None, str]:
    """
    Accept 10–15 digit numbers (India: 10 digits or 91 + 10 digits).
    Returns (normalized_digits, error_message). normalized is digits-only.
    """
    d = normalize_whatsapp_digits(raw)
    if len(d) < 10:
        return None, "Enter a valid WhatsApp number (at least 10 digits)."
    if len(d) > 15:
        return None, "WhatsApp number is too long."
    # Reject obviously invalid (all same digit)
    if len(set(d)) < 2:
        return None, "Please enter a real WhatsApp number."
    if len(d) == 11 and d.startswith("0"):
        d = d[1:]
        if len(d) != 10:
            return None, "Enter a valid WhatsApp number."
    if len(d) == 10:
        return d, ""
    if len(d) == 12 and d.startswith("91"):
        return d, ""
    if 10 <= len(d) <= 15:
        return d, ""
    return None, "Enter a valid WhatsApp number with country code."
