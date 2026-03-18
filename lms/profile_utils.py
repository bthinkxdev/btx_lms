"""Helpers for learner profiles: ensure row exists, badge tier, display."""
from __future__ import annotations

from django.contrib.auth import get_user_model

from lms.models import UserProfile

User = get_user_model()


def get_or_create_profile(user) -> UserProfile:
    """Every dashboard user should have a UserProfile (migration + signal + fallback)."""
    if not user or not user.is_authenticated:
        raise ValueError("Authenticated user required")
    profile, created = UserProfile.objects.get_or_create(
        user=user,
        defaults={
            "full_name": (user.get_full_name() or user.username or "")[:255],
        },
    )
    if created or not profile.public_slug:
        profile.save()
    # Backfill display name so dashboard/modals match the logged-in account
    if not (profile.full_name or "").strip():
        suggested = (user.get_full_name() or user.username or "").strip()[:255]
        if suggested:
            profile.full_name = suggested
            profile.save(update_fields=["full_name"])
    return profile


def refresh_profile_nudge_session(request) -> None:
    """After new enrollment, show profile prompt again if completion is low."""
    if not request.user.is_authenticated:
        return
    try:
        p = UserProfile.objects.get(user=request.user)
    except UserProfile.DoesNotExist:
        return
    if p.profile_completion < 40:
        request.session.pop("profile_nudge_dismissed", None)


def learner_badge(cert_count: int, enrollment_count: int, completion: int) -> tuple[str, str]:
    """
    Returns (label, css_modifier).
    Pro: certificate or very complete profile.
    Active: enrolled or halfway-complete profile.
    Beginner: default.
    """
    if cert_count >= 1 or completion >= 82:
        return "Pro Learner", "badge-pro"
    if enrollment_count >= 1 or completion >= 42:
        return "Active Learner", "badge-active"
    return "Beginner", "badge-beginner"
