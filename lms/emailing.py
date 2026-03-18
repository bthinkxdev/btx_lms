"""
Branded HTML + plain-text transactional emails.
Templates live in lms/templates/lms/emails/.
"""
from __future__ import annotations

import logging
from typing import Any

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone

logger = logging.getLogger(__name__)


def _public_base_url(request=None) -> str:
    if request is not None:
        try:
            return request.build_absolute_uri("/").rstrip("/")
        except Exception:
            pass
    return (getattr(settings, "LMS_PUBLIC_BASE_URL", "") or "").strip().rstrip("/")


def build_email_context(request=None, **extra: Any) -> dict[str, Any]:
    """Shared context for all LMS email templates."""
    base = _public_base_url(request)
    ctx = {
        "site_name": getattr(settings, "LMS_EMAIL_BRAND_NAME", "BThinkX"),
        "site_url": base,
        "site_url_display": base or "https://bthinkx.com",
        "tagline": getattr(settings, "LMS_IDENTITY_LABEL", "Professional AI learning"),
        "year": timezone.now().year,
        "support_email": getattr(settings, "CONTACT_EMAIL_TO", "")
        or getattr(settings, "DEFAULT_FROM_EMAIL", ""),
    }
    ctx.update(extra)
    return ctx


def send_branded_email(
    *,
    subject: str,
    template_name: str,
    to_emails: list[str],
    context: dict[str, Any] | None = None,
    request=None,
    fail_silently: bool = False,
    from_email: str | None = None,
) -> None:
    """
    Send multipart/alternative email using lms/emails/{template_name}.html and .txt
    """
    ctx = build_email_context(request, **(context or {}))
    html = render_to_string(f"lms/emails/{template_name}.html", ctx)
    text = render_to_string(f"lms/emails/{template_name}.txt", ctx)
    from_addr = from_email or getattr(
        settings, "DEFAULT_FROM_EMAIL", "noreply@example.com"
    )
    msg = EmailMultiAlternatives(
        subject=subject,
        body=text,
        from_email=from_addr,
        to=to_emails,
    )
    msg.attach_alternative(html, "text/html")
    msg.send(fail_silently=fail_silently)


def send_branded_email_safe(
    *,
    subject: str,
    template_name: str,
    to_emails: list[str],
    context: dict[str, Any] | None = None,
    request=None,
) -> bool:
    """Like send_branded_email but returns False on failure (logs exception)."""
    try:
        send_branded_email(
            subject=subject,
            template_name=template_name,
            to_emails=to_emails,
            context=context,
            request=request,
            fail_silently=False,
        )
        return True
    except Exception:
        logger.exception("Branded email send failed: %s → %s", template_name, to_emails)
        return False
