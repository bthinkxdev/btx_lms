"""Template context for conversion widgets (WhatsApp, pricing, countdown)."""
from urllib.parse import quote

from django.conf import settings

from lms.models import Enrollment


def _mentor_link_and_label():
    cal = (getattr(settings, "LMS_MENTOR_CALENDLY_URL", None) or "").strip()
    if cal:
        return cal, getattr(settings, "LMS_MENTOR_CTA_CALENDLY", "Book a call")
    wa = (getattr(settings, "LMS_WHATSAPP_NUMBER", None) or "").strip()
    if wa:
        msg = getattr(
            settings,
            "LMS_MENTOR_WHATSAPP_MESSAGE",
            "Hi, I'd like to speak with a mentor before enrolling.",
        )
        return f"https://wa.me/{wa}?text={quote(msg)}", getattr(
            settings, "LMS_MENTOR_CTA_WHATSAPP", "Talk to mentor"
        )
    return "", ""


def _show_sticky_enroll_bar(request):
    """Hide bottom enroll strip for logged-in users who are already enrolled."""
    if not getattr(request, "user", None) or not request.user.is_authenticated:
        return True
    return not Enrollment.objects.filter(user=request.user).exists()


def conversion(request):
    orig = int(getattr(settings, "LMS_ORIGINAL_PRICE_INR", 4999) or 0)
    sale = int(getattr(settings, "LMS_COURSE_PRICE_INR", 2499) or 0)
    mentor_url, mentor_cta = _mentor_link_and_label()
    return {
        "LMS_IDENTITY_LABEL": getattr(settings, "LMS_IDENTITY_LABEL", "AI Freelancer"),
        "LMS_MENTOR_URL": mentor_url,
        "LMS_MENTOR_CTA": mentor_cta,
        "LMS_LIVE_ACTIVITY_ENABLED": getattr(
            settings, "LMS_LIVE_ACTIVITY_ENABLED", True
        ),
        "LMS_WHATSAPP_NUMBER": getattr(settings, "LMS_WHATSAPP_NUMBER", "") or "",
        "LMS_WHATSAPP_MESSAGE": getattr(
            settings,
            "LMS_WHATSAPP_MESSAGE",
            "Hi, I'm interested in the Prompt Engineering course",
        ),
        "LMS_ORIGINAL_PRICE_INR": orig,
        "LMS_COURSE_PRICE_DISPLAY": sale,
        "LMS_SAVINGS_INR": max(0, orig - sale),
        "LMS_OFFER_COUNTDOWN_ISO": getattr(settings, "LMS_OFFER_COUNTDOWN_END", "") or "",
        "LMS_LIMITED_SEATS_TEXT": getattr(
            settings, "LMS_LIMITED_SEATS_TEXT", "Limited seats at launch price"
        ),
        "LMS_LEAD_MAGNET_PDF_URL": getattr(settings, "LMS_LEAD_MAGNET_PDF_URL", "") or "",
        "LMS_AB_VARIANT": request.COOKIES.get("lms_ab", "a"),
        "LMS_SEATS_LEFT": _seats_left(),
        "LMS_SHOW_STICKY_ENROLL_BAR": _show_sticky_enroll_bar(request),
    }


def _seats_left():
    total = int(getattr(settings, "LMS_TOTAL_SEATS", 0) or 0)
    if total <= 0:
        return None
    sold = Enrollment.objects.count()
    return max(0, total - sold)
