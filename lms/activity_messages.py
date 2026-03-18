"""
Build anonymized one-line messages for live activity proof (social proof).
"""
from __future__ import annotations

import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractUser

    from lms.models import Lead

# Indian regions for "Name from Place" style copy (privacy-friendly).
_ACTIVITY_REGIONS = (
    "Kerala",
    "Mumbai",
    "Bangalore",
    "Delhi NCR",
    "Hyderabad",
    "Pune",
    "Chennai",
    "Goa",
    "Kolkata",
    "Ahmedabad",
)


def _region(seed: int) -> str:
    return _ACTIVITY_REGIONS[abs(seed) % len(_ACTIVITY_REGIONS)]


def _display_name_from_user(user: AbstractUser | None) -> str:
    if user is None:
        return "Someone"
    fn = (getattr(user, "first_name", None) or "").strip()
    if fn:
        return fn.split()[0].title()[:24]
    un = (getattr(user, "username", None) or "").strip()
    if un and un.lower() not in ("", "user"):
        part = un.split("@")[0].split(".")[0]
        if part and len(part) > 1:
            return part.title()[:24]
    email = (getattr(user, "email", None) or "").strip()
    if email and "@" in email:
        local = email.split("@")[0].split(".")[0].split("+")[0]
        if local and local.isalnum() and len(local) > 1:
            return local.title()[:24]
    return "A learner"


def _display_name_from_lead(lead: Lead | None) -> str:
    if lead is None:
        return "Someone"
    name = (lead.name or "").strip()
    if name:
        return name.split()[0].title()[:24]
    email = (lead.email or "").strip()
    if email and "@" in email:
        local = email.split("@")[0].split(".")[0]
        if local and len(local) > 1:
            return local.title()[:24]
    if (lead.phone or "").strip():
        return "A learner"
    return "Someone"


def message_enrollment(user, *, enrollment_id: int) -> str:
    name = _display_name_from_user(user)
    place = _region(enrollment_id)
    return f"🔥 {name} from {place} just enrolled"


def message_lead(lead, *, lead_pk: int) -> str:
    name = _display_name_from_lead(lead)
    place = _region(lead_pk * 7)
    return f"✨ {name} from {place} joined the list"


def message_certificate(user, *, cert_id: int) -> str:
    name = _display_name_from_user(user)
    place = _region(cert_id * 13)
    return f"🏆 {name} from {place} earned their certificate"


def fallback_demo_messages(count: int = 6) -> list[str]:
    """When the feed is empty, optional subtle canned lines (generic, no fake names)."""
    pool = [
        "🔥 A learner from India just enrolled",
        "✨ Someone reserved their seat today",
        "🏆 New certificate unlocked this week",
    ]
    random.shuffle(pool)
    return pool[: min(count, len(pool))]
