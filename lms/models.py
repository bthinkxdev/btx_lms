"""
LMS models: Course, Module, Lesson, Enrollment, Exam, ExamResult, Certificate.
"""
import uuid
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.text import slugify


def generate_certificate_id() -> str:
    """Generate a unique certificate ID (e.g. LMS-XXXX-XXXX)."""
    part = uuid.uuid4().hex[:8].upper()
    return f"LMS-{part[:4]}-{part[4:]}"


class Course(models.Model):
    """Course model with slug and ordering."""
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, db_index=True)
    description = models.TextField(blank=True)
    thumbnail = models.URLField(blank=True, default="")
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    is_published = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["is_published"]),
        ]

    def __str__(self) -> str:
        return self.title

    def clean(self) -> None:
        if self.price is not None and self.price < 0:
            raise ValidationError({"price": "Price cannot be negative."})

    def save(self, *args, **kwargs) -> None:
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)


class Module(models.Model):
    """Day-wise release module belonging to a course."""
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="modules",
    )
    title = models.CharField(max_length=255)
    release_day = models.PositiveIntegerField(
        help_text="Day number when this module unlocks (1-based)."
    )
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "release_day"]
        unique_together = [["course", "release_day"]]
        indexes = [
            models.Index(fields=["course", "release_day"]),
        ]

    def __str__(self) -> str:
        return f"{self.course.title} – Day {self.release_day}: {self.title}"

    def clean(self) -> None:
        if self.release_day is not None and self.release_day < 1:
            raise ValidationError({"release_day": "Release day must be at least 1."})


class Lesson(models.Model):
    """Lesson with S3 video key; day unlock via module.release_day."""
    module = models.ForeignKey(
        Module,
        on_delete=models.CASCADE,
        related_name="lessons",
    )
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, db_index=True)
    video_key = models.CharField(
        max_length=512,
        blank=True,
        default="",
        help_text="S3 object key for private video.",
    )
    order = models.PositiveIntegerField(default=0)
    duration_seconds = models.PositiveIntegerField(null=True, blank=True)
    free_preview = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Allow public access at /courses/…/preview/… without enrollment.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order"]
        unique_together = [["module", "slug"]]
        indexes = [
            models.Index(fields=["module", "slug"]),
        ]

    def __str__(self) -> str:
        return self.title

    def save(self, *args, **kwargs) -> None:
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def get_release_day(self) -> int:
        """Return the release day number from the parent module."""
        return self.module.release_day if self.module_id else 0

    def get_unlock_date(self, user) -> "datetime | None":
        """Return the date when this lesson unlocks for the user (purchase_date + release_day)."""
        from django.utils import timezone
        from datetime import timedelta
        if user is None or not user.is_authenticated:
            return None
        # Legacy date-based unlocking is no longer used; progression is based on
        # per-day quizzes instead. Keep this method for backwards compatibility.
        # Return enrollment date + (release_day - 1) for display if needed.
        enrollment = (
            Enrollment.objects.filter(
                user=user,
                course_id=self.module.course_id,
            )
            .order_by("-enrolled_at")
            .first()
        )
        if not enrollment:
            return None
        base = enrollment.enrolled_at or timezone.now().date()
        if hasattr(base, "date"):
            base = base.date()
        return base + timedelta(days=self.get_release_day() - 1)

    def is_unlocked(self, user) -> bool:
        """
        Check if lesson is unlocked for user.

        Day 1 lessons are available as soon as the user is enrolled.
        For later days, the previous day's quiz must be passed (score >= 6).
        """
        if user is None or not user.is_authenticated:
            return False

        # Must be enrolled in the course
        if not Enrollment.objects.filter(
            user=user,
            course_id=self.module.course_id,
        ).exists():
            return False

        # Day 1 is always available once enrolled
        day = self.get_release_day()
        if day <= 1:
            return True

        # For day N (>1), require pass in day N-1 quiz
        from lms.models import DayQuizResult, Module  # local import to avoid cycles

        prev_module = (
            Module.objects.filter(
                course_id=self.module.course_id,
                release_day=day - 1,
            )
            .order_by("order", "id")
            .first()
        )
        if not prev_module:
            # If previous day module is missing, don't block progression.
            return True

        return DayQuizResult.objects.filter(
            user=user,
            module=prev_module,
            passed=True,
        ).exists()

    def get_signed_video_url(self, user, expiry_seconds: int = 300) -> str | None:
        """Return a presigned S3 URL for the lesson video; None if no key or not unlocked."""
        from lms.services import s3_generate_presigned_url
        if not self.video_key or not self.is_unlocked(user):
            return None
        return s3_generate_presigned_url(self.video_key, expiry_seconds=expiry_seconds)


class Enrollment(models.Model):
    """User enrollment in a course (created after payment success)."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="enrollments",
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="enrollments",
    )
    enrolled_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        unique_together = [["user", "course"]]
        ordering = ["-enrolled_at"]
        indexes = [
            models.Index(fields=["user", "course"]),
        ]

    def __str__(self) -> str:
        return f"{self.user} – {self.course.title}"


class Exam(models.Model):
    """Exam linked to a course; pass/fail via ExamResult."""
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="exams",
    )
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, db_index=True)
    description = models.TextField(blank=True)
    passing_score = models.PositiveIntegerField(
        default=60,
        help_text="Minimum score (0-100) to pass.",
    )
    is_published = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [["course", "slug"]]
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["course", "slug"]),
        ]

    def __str__(self) -> str:
        return f"{self.course.title} – {self.title}"

    def clean(self) -> None:
        if self.passing_score is not None and (self.passing_score < 0 or self.passing_score > 100):
            raise ValidationError({"passing_score": "Passing score must be between 0 and 100."})


class ExamResult(models.Model):
    """Exam result (score uploaded by admin); determines pass/fail."""
    exam = models.ForeignKey(
        Exam,
        on_delete=models.CASCADE,
        related_name="results",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="exam_results",
    )
    score = models.PositiveIntegerField(
        help_text="Score 0-100.",
    )
    passed = models.BooleanField(default=False, db_index=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = [["exam", "user"]]
        ordering = ["-uploaded_at"]
        indexes = [
            models.Index(fields=["exam", "user"]),
            models.Index(fields=["user", "passed"]),
        ]

    def __str__(self) -> str:
        return f"{self.exam.title} – {self.user} – {self.score}"

    def clean(self) -> None:
        if self.score is not None and (self.score < 0 or self.score > 100):
            raise ValidationError({"score": "Score must be between 0 and 100."})

    def save(self, *args, **kwargs) -> None:
        if self.exam_id and self.score is not None:
            self.passed = self.score >= self.exam.passing_score
        super().save(*args, **kwargs)

    def is_passed(self) -> bool:
        """Return whether this result is a pass."""
        return bool(self.passed)


class DayQuizQuestion(models.Model):
    """
    Ten-question daily quiz for each module/day.
    Each question has 4 options and a single correct answer.
    """
    module = models.ForeignKey(
        Module,
        on_delete=models.CASCADE,
        related_name="day_quiz_questions",
    )
    text = models.TextField()
    option_1 = models.CharField(max_length=255)
    option_2 = models.CharField(max_length=255)
    option_3 = models.CharField(max_length=255)
    option_4 = models.CharField(max_length=255)
    correct_option = models.PositiveSmallIntegerField(
        choices=[(1, "Option 1"), (2, "Option 2"), (3, "Option 3"), (4, "Option 4")],
    )
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["module", "order", "id"]
        indexes = [
            models.Index(fields=["module", "order"]),
        ]

    def __str__(self) -> str:
        return f"Day {self.module.release_day} – Q{self.order or self.pk}"


class DayQuizResult(models.Model):
    """
    Per-day quiz result (score out of 10). Passing score is >= 6.
    Used to unlock the next day's lessons.
    """
    module = models.ForeignKey(
        Module,
        on_delete=models.CASCADE,
        related_name="day_quiz_results",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="day_quiz_results",
    )
    score = models.PositiveIntegerField()
    passed = models.BooleanField(default=False, db_index=True)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [["module", "user"]]
        ordering = ["-submitted_at"]
        indexes = [
            models.Index(fields=["module", "user"]),
            models.Index(fields=["user", "passed"]),
        ]

    def __str__(self) -> str:
        return f"{self.user} – Day {self.module.release_day} – {self.score}/10"

    def save(self, *args, **kwargs) -> None:
        # 6 or more marks to pass
        self.passed = self.score >= 6
        super().save(*args, **kwargs)


class Certificate(models.Model):
    """Certificate with unique ID, optional PDF; QR/verification via certificate_id."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="certificates",
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="certificates",
    )
    certificate_id = models.CharField(
        max_length=32,
        unique=True,
        db_index=True,
        editable=False,
    )
    pdf_file = models.FileField(upload_to="certificates/%Y/%m/", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [["user", "course"]]
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["certificate_id"]),
            models.Index(fields=["user", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.certificate_id} – {self.user} – {self.course.title}"

    def save(self, *args, **kwargs) -> None:
        if not self.certificate_id:
            while True:
                cid = generate_certificate_id()
                if not Certificate.objects.filter(certificate_id=cid).exists():
                    self.certificate_id = cid
                    break
        super().save(*args, **kwargs)

    @staticmethod
    def generate_certificate_id() -> str:
        """Generate a unique certificate ID."""
        return generate_certificate_id()


class UserProfile(models.Model):
    """
    Extended learner profile (OneToOne with User). Completion % drives UX nudges.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="lms_profile",
    )
    full_name = models.CharField(max_length=255, blank=True, default="")
    phone = models.CharField(max_length=32, blank=True, default="")
    location = models.CharField(max_length=255, blank=True, default="")
    profile_photo = models.ImageField(
        upload_to="profiles/%Y/%m/",
        blank=True,
        null=True,
        help_text="Square photo works best.",
    )
    highest_education = models.CharField(max_length=128, blank=True, default="")
    college = models.CharField(max_length=255, blank=True, default="")
    graduation_year = models.PositiveSmallIntegerField(null=True, blank=True)
    experience = models.TextField(blank=True, default="")
    skills = models.TextField(
        blank=True,
        default="",
        help_text="Comma-separated, e.g. Prompt Engineering, Python",
    )
    linkedin_url = models.URLField(blank=True, default="")
    portfolio_url = models.URLField(blank=True, default="")
    bio = models.TextField(max_length=500, blank=True, default="")
    profile_completion = models.PositiveSmallIntegerField(default=0, editable=False)
    public_slug = models.SlugField(
        max_length=40,
        unique=True,
        db_index=True,
        help_text="Legacy slug URL; primary share link is /u/your-username/.",
    )
    is_public = models.BooleanField(
        default=True,
        db_index=True,
        help_text="If off, /u/username/ returns 404.",
    )
    public_whatsapp_contact = models.BooleanField(
        default=False,
        help_text="Show WhatsApp contact on public portfolio (uses profile phone).",
    )
    public_email_contact = models.BooleanField(
        default=False,
        help_text="Show email contact on public portfolio (uses account email).",
    )
    available_for_freelance = models.BooleanField(
        default=False,
        help_text="Show “Available for freelance” on public portfolio.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "User profile"
        verbose_name_plural = "User profiles"

    def __str__(self) -> str:
        return f"Profile: {self.user_id}"

    @property
    def display_name(self) -> str:
        name = (self.full_name or "").strip()
        if name:
            return name
        fn = self.user.get_full_name() if self.user_id else ""
        if fn.strip():
            return fn.strip()
        return self.user.username if self.user_id else ""

    def _skill_tokens(self) -> list[str]:
        return [t.strip() for t in (self.skills or "").split(",") if t.strip()]

    @property
    def skills_list(self) -> list[str]:
        return self._skill_tokens()

    def compute_completion(self) -> int:
        """Weighted completion 0–100 (photo, basic, education, experience, skills, social)."""
        score = 0.0
        photo_name = ""
        if self.profile_photo:
            photo_name = getattr(self.profile_photo, "name", "") or ""
        if photo_name:
            score += 15
        if (self.full_name or "").strip():
            score += 5
        if (self.phone or "").strip():
            score += 5
        if (self.location or "").strip():
            score += 5
        if (self.bio or "").strip():
            score += 5
        edu = 0
        if (self.highest_education or "").strip():
            edu += 1
        if (self.college or "").strip():
            edu += 1
        if self.graduation_year:
            edu += 1
        if edu >= 3:
            score += 20
        elif edu == 2:
            score += 13
        elif edu == 1:
            score += 7
        ex = (self.experience or "").strip()
        if len(ex) >= 80:
            score += 15
        elif len(ex) >= 25:
            score += 10
        elif len(ex) > 0:
            score += 5
        n_skills = len(self._skill_tokens())
        if n_skills >= 3:
            score += 15
        elif n_skills == 2:
            score += 10
        elif n_skills == 1:
            score += 5
        li = bool((self.linkedin_url or "").strip())
        po = bool((self.portfolio_url or "").strip())
        if li and po:
            score += 15
        elif li or po:
            score += 7.5
        return min(100, int(round(score)))

    def _ensure_public_slug(self) -> None:
        if self.public_slug:
            return
        import secrets

        UserProfile = type(self)
        for _ in range(50):
            raw = secrets.token_urlsafe(12).replace("-", "x")[:12].lower()
            slug = f"u{raw}"
            qs = UserProfile.objects.filter(public_slug=slug)
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            if not qs.exists():
                self.public_slug = slug
                return
        self.public_slug = f"u{self.user_id}_{secrets.token_hex(4)}"

    def save(self, *args, **kwargs) -> None:
        self._ensure_public_slug()
        self.profile_completion = self.compute_completion()
        super().save(*args, **kwargs)


class Lead(models.Model):
    """Marketing lead capture (lead magnet, exit intent, pre-payment)."""

    name = models.CharField(max_length=255, blank=True, default="")
    email = models.EmailField(blank=True, default="", db_index=True)
    phone = models.CharField(
        max_length=32,
        blank=True,
        default="",
        db_index=True,
        help_text="WhatsApp; required for new lead capture via API.",
    )
    source = models.CharField(
        max_length=64,
        blank=True,
        default="",
        help_text="e.g. lead_magnet, exit_intent, pre_payment, inline",
    )
    variant = models.CharField(
        max_length=8,
        blank=True,
        default="",
        help_text="A/B test bucket (a, b, …).",
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["source", "created_at"]),
        ]

    def __str__(self) -> str:
        key = self.email or self.phone or f"#{self.pk}"
        return f"{key} ({self.source or 'unknown'})"


class Testimonial(models.Model):
    """Social proof for landing and course pages."""

    name = models.CharField(max_length=255)
    photo = models.ImageField(upload_to="testimonials/photos/", blank=True, null=True)
    content = models.TextField()
    rating = models.PositiveSmallIntegerField(
        default=5,
        help_text="1–5 stars.",
    )
    proof_image = models.ImageField(
        upload_to="testimonials/proof/",
        blank=True,
        null=True,
        help_text="Optional screenshot (earnings, feedback, etc.).",
    )
    is_featured = models.BooleanField(default=False, db_index=True)
    is_published = models.BooleanField(default=True, db_index=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-is_featured", "sort_order", "-id"]

    def __str__(self) -> str:
        return f"{self.name} ({self.rating}★)"


class CaseStudy(models.Model):
    """Before/after proof blocks."""

    title = models.CharField(max_length=255)
    before_text = models.TextField()
    after_text = models.TextField()
    result_metrics = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="e.g. +40% response rate, 2x interview calls",
    )
    image = models.ImageField(upload_to="case_studies/", blank=True, null=True)
    is_published = models.BooleanField(default=True, db_index=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "-id"]
        verbose_name_plural = "Case studies"

    def __str__(self) -> str:
        return self.title


class LeadEvent(models.Model):
    """Funnel events for automation (email / WhatsApp hooks)."""

    class EventType(models.TextChoices):
        LEAD_CREATED = "lead_created", "Lead created"
        VIEWED_PRICING = "viewed_pricing", "Viewed pricing"
        CHECKOUT_STARTED = "checkout_started", "Checkout started"
        CHECKOUT_ABANDONED = "checkout_abandoned", "Checkout abandoned (no pay)"

    lead = models.ForeignKey(
        Lead,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="events",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lead_events",
    )
    event_type = models.CharField(max_length=64, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["event_type", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.event_type} @ {self.created_at}"


class ActivityEvent(models.Model):
    """
    Social-proof feed: anonymized one-liners (enrollment, lead, certificate).
    Shown in the corner UI; populated automatically via signals.
    """

    class ActivityType(models.TextChoices):
        ENROLLMENT = "enrollment", "Enrollment"
        LEAD = "lead", "New lead"
        CERTIFICATE = "certificate", "Certificate earned"

    activity_type = models.CharField(max_length=32, db_index=True)
    message = models.CharField(max_length=220)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["-created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.activity_type}: {self.message[:50]}"


class ReferralProfile(models.Model):
    """Unique referral code per user (sharer)."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="referral_profile",
    )
    code = models.CharField(max_length=16, unique=True, db_index=True)

    class Meta:
        ordering = ["-user_id"]

    def __str__(self) -> str:
        return f"{self.user} → {self.code}"


class Referral(models.Model):
    """Someone enrolled via a referrer’s link."""

    class RewardStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        GRANTED = "granted", "Granted"
        NA = "na", "N/A"

    referrer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="referrals_sent",
    )
    referred_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="referral_received",
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="referrals",
    )
    reward_status = models.CharField(
        max_length=16,
        choices=RewardStatus.choices,
        default=RewardStatus.PENDING,
    )
    discount_percent_used = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [["referred_user", "course"]]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.referrer} → {self.referred_user} ({self.course})"
