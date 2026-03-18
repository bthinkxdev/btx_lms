"""Referral code helpers."""
import secrets

from lms.models import ReferralProfile


def get_or_create_referral_profile(user):
    """Ensure any user (including pre-migration accounts) has a referral code."""
    existing = ReferralProfile.objects.filter(user=user).first()
    if existing and existing.code:
        return existing
    for _ in range(40):
        code = secrets.token_hex(4).upper()[:10]
        if ReferralProfile.objects.filter(code=code).exists():
            continue
        if existing:
            existing.code = code
            existing.save(update_fields=["code"])
            return existing
        return ReferralProfile.objects.create(user=user, code=code)
    raise RuntimeError("Could not allocate referral code")
