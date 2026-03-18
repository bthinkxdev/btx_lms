import secrets
from dataclasses import dataclass
from datetime import timedelta
from typing import Optional

from django.contrib.auth import get_user_model
from django.utils import timezone


OTP_SESSION_KEY = "email_login_otp"
OTP_ATTEMPTS_KEY = "email_login_otp_attempts"
OTP_MAX_FAILED_ATTEMPTS = 5


@dataclass
class OTPState:
    email: str
    code: str
    expires_at: timezone.datetime


def generate_otp_code(length: int = 6) -> str:
    """Cryptographically strong numeric OTP (single use per successful verify)."""
    upper = 10**length - 1
    return f"{secrets.randbelow(upper + 1):0{length}d}"


def create_otp_for_email(session, email: str, ttl_minutes: int = 10) -> OTPState:
    """Create and store an OTP in the session for the given email."""
    code = generate_otp_code()
    expires_at = timezone.now() + timedelta(minutes=ttl_minutes)
    state = OTPState(email=email, code=code, expires_at=expires_at)
    session[OTP_SESSION_KEY] = {
        "email": state.email,
        "code": state.code,
        "expires_at": state.expires_at.isoformat(),
    }
    session.modified = True
    return state


def get_otp_state(session) -> Optional[OTPState]:
    """Return the current OTP state from the session, or None if missing/invalid."""
    data = session.get(OTP_SESSION_KEY)
    if not data:
        return None
    try:
        expires_at = timezone.datetime.fromisoformat(data["expires_at"])
        if timezone.is_naive(expires_at):
            expires_at = timezone.make_aware(expires_at, timezone.get_current_timezone())
    except Exception:
        return None
    return OTPState(email=data.get("email", ""), code=data.get("code", ""), expires_at=expires_at)


def clear_otp_state(session) -> None:
    """Remove any stored OTP state from the session."""
    if OTP_SESSION_KEY in session:
        del session[OTP_SESSION_KEY]
    session.pop(OTP_ATTEMPTS_KEY, None)
    session.modified = True


def record_failed_otp_attempt(session) -> bool:
    """
    Increment failed verify attempts.
    Returns True if max attempts exceeded (caller should clear OTP state).
    """
    n = int(session.get(OTP_ATTEMPTS_KEY, 0) or 0) + 1
    session[OTP_ATTEMPTS_KEY] = n
    session.modified = True
    return n >= OTP_MAX_FAILED_ATTEMPTS


def store_otp_in_session(session, email: str, code: str, ttl_minutes: int = 10) -> OTPState:
    """Persist OTP after email was sent successfully."""
    expires_at = timezone.now() + timedelta(minutes=ttl_minutes)
    session[OTP_SESSION_KEY] = {
        "email": email,
        "code": code,
        "expires_at": expires_at.isoformat(),
    }
    session.pop(OTP_ATTEMPTS_KEY, None)
    session.modified = True
    return OTPState(email=email, code=code, expires_at=expires_at)


def find_user_by_email(email: str):
    """Return the first active user matching the email (case-insensitive), or None."""
    if not email:
        return None
    User = get_user_model()
    return (
        User.objects.filter(email__iexact=email, is_active=True)
        .order_by("id")
        .first()
    )

