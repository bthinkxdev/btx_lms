"""
Lead follow-up: branded HTML email + WhatsApp automation hooks.
"""
import logging

from django.conf import settings
from django.urls import reverse

logger = logging.getLogger(__name__)
wa_logger = logging.getLogger("lms.whatsapp")


def _absolute_url(path: str) -> str:
    base = (getattr(settings, "LMS_PUBLIC_BASE_URL", "") or "").strip().rstrip("/")
    if not base:
        return ""
    if not path.startswith("/"):
        path = "/" + path
    return base + path


def _enroll_url() -> str:
    try:
        return _absolute_url(reverse("lms:course_list")) + "#enroll"
    except Exception:
        return _absolute_url("/courses/") + "#enroll"


def _home_url() -> str:
    try:
        return _absolute_url(reverse("lms:home"))
    except Exception:
        return _absolute_url("/")


def followup_email_context(event_type: str) -> dict:
    """Rich copy + layout context for lms/emails/followup_generic.*"""
    enroll = _enroll_url()
    home = _home_url()
    brand = getattr(settings, "LMS_EMAIL_BRAND_NAME", "BThinkX")

    configs = {
        "lead_created": {
            "preheader": f"Welcome! You’re on the {brand} list. Prompts & updates ahead.",
            "headline": "You’re on the list",
            "paragraphs": [
                "Thanks for raising your hand, we’re glad you’re here.",
                "We’ll send useful prompt ideas, course updates, and occasional offers to this inbox. No fluff.",
            ],
            "bullets": [
                "Actionable AI prompt patterns for real work",
                "Launch updates & limited-seat pricing",
                "Unsubscribe anytime from future messages",
            ],
            "cta_url": home or enroll,
            "cta_label": f"Explore {brand}",
            "footer_line": "You received this after sharing your email with us.",
        },
        "viewed_pricing": {
            "preheader": "Still deciding? Here’s what you get with full enrollment.",
            "headline": "Still thinking? Here’s the full picture",
            "paragraphs": [
                "You checked our pricing. Here’s a quick recap of what full access includes.",
                "The program is built around daily lessons and quiz-gated progression, so you actually finish instead of only watching videos.",
            ],
            "bullets": [
                "Structured day-by-day modules + practice",
                "Quiz unlocks to keep momentum",
                "Verified certificate employers can check",
            ],
            "cta_url": enroll,
            "cta_label": "View enrollment & pricing",
            "footer_line": "You received this after viewing pricing on our site.",
        },
        "checkout_started": {
            "preheader": "Complete payment to unlock Day 1 instantly.",
            "headline": "You’re one step away",
            "paragraphs": [
                "You started checkout. Great choice.",
                "Complete payment to unlock Day 1 right away and begin the full program.",
            ],
            "bullets": [],
            "cta_url": enroll,
            "cta_label": "Complete enrollment",
            "footer_line": "You received this after starting checkout.",
        },
        "checkout_abandoned": {
            "preheader": "Your spot is waiting, finish when you’re ready.",
            "headline": "Pick up where you left off",
            "paragraphs": [
                "It looks like payment wasn’t completed. No problem.",
                "Your enrollment is still available whenever you’re ready. If you hit a technical issue, just reply to this email.",
            ],
            "bullets": [],
            "cta_url": enroll,
            "cta_label": "Continue to checkout",
            "footer_line": "You received this after an incomplete checkout.",
        },
    }
    ctx = dict(configs.get(event_type) or {})
    if not ctx:
        ctx = {
            "preheader": f"Update from {brand}",
            "headline": f"Hello from {brand}",
            "paragraphs": ["Thanks for engaging with our programs."],
            "bullets": [],
            "cta_url": enroll or home,
            "cta_label": "Visit website",
            "footer_line": "",
        }
    if not ctx.get("cta_url"):
        ctx["cta_url"] = home or ""
    if not ctx.get("cta_label"):
        ctx["cta_label"] = "Visit website"
    return ctx


def notify_lead_pipeline(event_type: str, *, lead=None, user=None, email: str = "", extra=None) -> None:
    """
    Record-side effects are handled by LeadEvent; this sends branded follow-up email.
    """
    extra = extra or {}
    to_email = ""
    if lead and lead.email:
        to_email = lead.email.strip()
    elif email:
        to_email = email.strip()
    elif user and getattr(user, "email", None):
        to_email = (user.email or "").strip()

    subject_map = {
        "lead_created": getattr(settings, "LMS_FOLLOWUP_LEAD_SUBJECT", "You're in | BThinkX"),
        "viewed_pricing": "Still thinking? Here's what you get",
        "checkout_started": "Complete your enrollment",
        "checkout_abandoned": "Your spot is waiting · finish checkout",
    }
    subject = subject_map.get(
        event_type, f"{getattr(settings, 'LMS_EMAIL_BRAND_NAME', 'BThinkX')} update"
    )

    if to_email and getattr(settings, "LMS_FOLLOWUP_SEND_EMAIL", False):
        try:
            from lms.emailing import send_branded_email

            ctx = followup_email_context(event_type)
            send_branded_email(
                subject=subject,
                template_name="followup_generic",
                to_emails=[to_email],
                context=ctx,
                request=None,
                fail_silently=True,
            )
        except Exception as exc:
            logger.debug("Follow-up email skipped: %s", exc)

    phone = ""
    if lead and lead.phone:
        phone = lead.phone.strip()
    wa_logger.info(
        "WA_PLACEHOLDER event=%s phone=%s email=%s extra=%s",
        event_type,
        phone or "-",
        to_email or "-",
        extra,
    )
