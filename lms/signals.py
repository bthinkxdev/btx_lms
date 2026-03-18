"""
LMS signals: certificate creation on exam pass, lead funnel, referral profiles.
"""
from django.contrib.auth import get_user_model
from django.dispatch import receiver

from django.db.models.signals import post_save

from lms.activity_messages import message_certificate, message_enrollment, message_lead
from lms.models import (
    ActivityEvent,
    Certificate,
    Enrollment,
    ExamResult,
    Lead,
    LeadEvent,
    ReferralProfile,
    UserProfile,
)


@receiver(post_save, sender=ExamResult)
def create_certificate_on_exam_pass(sender, instance, created, **kwargs):
    """Create certificate when user passes exam (admin uploads score)."""
    if not instance.is_passed():
        return
    exam = instance.exam
    if exam is None or exam.course_id is None:
        return
    user = instance.user
    if user is None:
        return
    if Certificate.objects.filter(user=user, course=exam.course).exists():
        return
    cert = Certificate.objects.create(user=user, course=exam.course)
    try:
        from lms.services import certificate_generate_pdf

        certificate_generate_pdf(cert)
    except Exception:
        pass


@receiver(post_save, sender=Lead)
def on_lead_created_pipeline(sender, instance, created, **kwargs):
    if not created:
        return
    LeadEvent.objects.create(
        lead=instance, event_type=LeadEvent.EventType.LEAD_CREATED.value
    )
    try:
        from django.conf import settings

        if getattr(settings, "LMS_LIVE_ACTIVITY_ENABLED", True):
            ActivityEvent.objects.create(
                activity_type=ActivityEvent.ActivityType.LEAD.value,
                message=message_lead(instance, lead_pk=instance.pk),
            )
    except Exception:
        pass
    try:
        from lms.followup import notify_lead_pipeline

        notify_lead_pipeline("lead_created", lead=instance)
    except Exception:
        pass


@receiver(post_save, sender=Enrollment)
def activity_on_enrollment(sender, instance, created, **kwargs):
    if not created:
        return
    try:
        from django.conf import settings

        if not getattr(settings, "LMS_LIVE_ACTIVITY_ENABLED", True):
            return
        ActivityEvent.objects.create(
            activity_type=ActivityEvent.ActivityType.ENROLLMENT.value,
            message=message_enrollment(instance.user, enrollment_id=instance.pk),
        )
    except Exception:
        pass


@receiver(post_save, sender=Certificate)
def activity_on_certificate(sender, instance, created, **kwargs):
    if not created:
        return
    try:
        from django.conf import settings

        if not getattr(settings, "LMS_LIVE_ACTIVITY_ENABLED", True):
            return
        ActivityEvent.objects.create(
            activity_type=ActivityEvent.ActivityType.CERTIFICATE.value,
            message=message_certificate(instance.user, cert_id=instance.pk),
        )
    except Exception:
        pass


@receiver(post_save, sender=get_user_model())
def ensure_referral_profile(sender, instance, created, **kwargs):
    """Create referral code for new users (OTP signup)."""
    if not created:
        return
    if ReferralProfile.objects.filter(user=instance).exists():
        return
    import secrets

    for _ in range(30):
        code = secrets.token_hex(4).upper()[:10]
        if not ReferralProfile.objects.filter(code=code).exists():
            ReferralProfile.objects.create(user=instance, code=code)
            break


@receiver(post_save, sender=get_user_model())
def ensure_user_profile(sender, instance, created, **kwargs):
    """Auto-create learner profile for OTP and password registration."""
    if not created:
        return
    if UserProfile.objects.filter(user=instance).exists():
        return
    fn = (instance.get_full_name() or instance.username or "")[:255]
    UserProfile.objects.create(user=instance, full_name=fn)
