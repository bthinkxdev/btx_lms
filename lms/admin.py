"""
LMS admin: Course, Module, Lesson, Enrollment, Exam, ExamResult,
DayQuizQuestion, DayQuizResult, Certificate.
"""
from django.contrib import admin

from lms.models import (
    ActivityEvent,
    CaseStudy,
    Certificate,
    Course,
    DayQuizQuestion,
    DayQuizResult,
    Enrollment,
    Exam,
    ExamResult,
    Lead,
    LeadEvent,
    Lesson,
    Module,
    Referral,
    ReferralProfile,
    Testimonial,
    UserProfile,
)


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("title", "slug", "price", "is_published", "created_at")
    list_filter = ("is_published",)
    search_fields = ("title", "slug")
    prepopulated_fields = {"slug": ("title",)}
    readonly_fields = ("created_at", "updated_at")


class LessonInline(admin.StackedInline):
    model = Lesson
    extra = 0
    ordering = ("order",)
    fields = ("title", "slug", "free_preview", "video_key", "order", "duration_seconds")


class DayQuizQuestionInline(admin.TabularInline):
    model = DayQuizQuestion
    extra = 0
    ordering = ("order", "id")
    fields = ("text", "option_1", "option_2", "option_3", "option_4", "correct_option", "order")


@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ("title", "course", "release_day", "order", "created_at")
    list_filter = ("course",)
    search_fields = ("title",)
    ordering = ("course", "order", "release_day")
    inlines = (LessonInline, DayQuizQuestionInline)


@admin.register(DayQuizQuestion)
class DayQuizQuestionAdmin(admin.ModelAdmin):
    list_display = ("module", "order", "text_preview", "correct_option")
    list_filter = ("module__course", "module__release_day")
    search_fields = ("text",)
    ordering = ("module", "order", "id")
    list_select_related = ("module", "module__course")

    def text_preview(self, obj):
        if not obj.text:
            return ""
        return obj.text[:80] + "…" if len(obj.text) > 80 else obj.text
    text_preview.short_description = "Question"


@admin.register(DayQuizResult)
class DayQuizResultAdmin(admin.ModelAdmin):
    list_display = ("user", "module", "score", "passed", "submitted_at")
    list_filter = ("module__course", "passed", "module__release_day")
    search_fields = ("user__username", "user__email")
    ordering = ("-submitted_at",)
    readonly_fields = ("submitted_at",)
    raw_id_fields = ("user",)
    list_select_related = ("module", "module__course", "user")


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ("title", "module", "free_preview", "slug", "order", "created_at")
    list_filter = ("module__course", "free_preview")
    search_fields = ("title", "slug")
    prepopulated_fields = {"slug": ("title",)}
    readonly_fields = ("created_at", "updated_at")


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ("user", "course", "enrolled_at")
    list_filter = ("course", "enrolled_at")
    search_fields = ("user__username", "course__title")
    readonly_fields = ("enrolled_at",)


@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ("title", "course", "passing_score", "is_published", "created_at")
    list_filter = ("course", "is_published")
    search_fields = ("title", "slug")
    prepopulated_fields = {"slug": ("title",)}
    readonly_fields = ("created_at", "updated_at")


@admin.register(ExamResult)
class ExamResultAdmin(admin.ModelAdmin):
    list_display = ("exam", "user", "score", "passed", "uploaded_at")
    list_filter = ("exam", "passed")
    search_fields = ("user__username", "exam__title")
    readonly_fields = ("uploaded_at",)
    raw_id_fields = ("user",)

    def save_model(self, request, obj, form, change):
        if obj.exam_id and obj.score is not None:
            obj.passed = obj.score >= obj.exam.passing_score
        super().save_model(request, obj, form, change)


@admin.register(ActivityEvent)
class ActivityEventAdmin(admin.ModelAdmin):
    list_display = ("message", "activity_type", "created_at")
    list_filter = ("activity_type",)
    ordering = ("-created_at",)
    readonly_fields = ("created_at",)


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ("phone", "email", "name", "source", "variant", "created_at")
    list_filter = ("source", "variant", "created_at")
    search_fields = ("email", "name", "phone")
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)


@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = ("name", "rating", "is_featured", "is_published", "sort_order")
    list_filter = ("is_featured", "is_published", "rating")
    search_fields = ("name", "content")
    ordering = ("-is_featured", "sort_order", "-id")


@admin.register(CaseStudy)
class CaseStudyAdmin(admin.ModelAdmin):
    list_display = ("title", "result_metrics", "is_published", "sort_order")
    list_filter = ("is_published",)
    search_fields = ("title", "before_text", "after_text")


@admin.register(LeadEvent)
class LeadEventAdmin(admin.ModelAdmin):
    list_display = ("event_type", "lead", "user", "created_at")
    list_filter = ("event_type", "created_at")
    search_fields = ("lead__email",)
    readonly_fields = ("created_at",)
    raw_id_fields = ("lead", "user")
    date_hierarchy = "created_at"


@admin.register(ReferralProfile)
class ReferralProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "code")
    search_fields = ("user__username", "user__email", "code")
    raw_id_fields = ("user",)


@admin.register(Referral)
class ReferralAdmin(admin.ModelAdmin):
    list_display = ("referrer", "referred_user", "course", "reward_status", "discount_percent_used", "created_at")
    list_filter = ("reward_status", "course")
    raw_id_fields = ("referrer", "referred_user")
    readonly_fields = ("created_at",)


@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = ("certificate_id", "user", "course", "created_at", "has_pdf")
    list_filter = ("course", "created_at")
    search_fields = ("certificate_id", "user__username", "course__title")
    readonly_fields = ("certificate_id", "created_at")

    def has_pdf(self, obj):
        return bool(obj and obj.pdf_file)
    has_pdf.boolean = True
    has_pdf.short_description = "PDF"


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "full_name",
        "is_public",
        "phone",
        "profile_completion",
        "updated_at",
    )
    list_filter = ("profile_completion", "is_public", "available_for_freelance")
    search_fields = (
        "full_name",
        "phone",
        "skills",
        "college",
        "user__username",
        "user__email",
    )
    raw_id_fields = ("user",)
    readonly_fields = (
        "profile_completion",
        "public_slug",
        "created_at",
        "updated_at",
    )

    fieldsets = (
        (
            "User",
            {"fields": ("user",)},
        ),
        (
            "Basic",
            {"fields": ("full_name", "phone", "location", "profile_photo", "bio")},
        ),
        (
            "Education",
            {"fields": ("highest_education", "college", "graduation_year")},
        ),
        (
            "Experience & skills",
            {"fields": ("experience", "skills")},
        ),
        (
            "Social",
            {"fields": ("linkedin_url", "portfolio_url")},
        ),
        (
            "Public portfolio",
            {
                "fields": (
                    "is_public",
                    "public_whatsapp_contact",
                    "public_email_contact",
                    "available_for_freelance",
                )
            },
        ),
        (
            "System",
            {
                "fields": (
                    "profile_completion",
                    "public_slug",
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )

