"""
LMS class-based views and mixins.
"""
import json
import logging
import re
from urllib.parse import quote

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Prefetch
from django.http import (
    Http404,
    HttpResponseForbidden,
    HttpResponsePermanentRedirect,
    HttpResponseRedirect,
    JsonResponse,
)
from django.shortcuts import get_object_or_404, redirect
from django.utils.html import strip_tags
from django.urls import reverse, reverse_lazy
from django.views.generic import (
    CreateView,
    DetailView,
    FormView,
    ListView,
    TemplateView,
    View,
)

from lms.forms import (
    EnrollForm,
    ProfileBasicSectionForm,
    ProfileBioSectionForm,
    ProfileEducationSectionForm,
    ProfileExperienceSectionForm,
    ProfilePortfolioSectionForm,
    ProfileSkillsSectionForm,
    RegisterForm,
)
from lms.models import (
    ActivityEvent,
    CaseStudy,
    Certificate,
    Course,
    Enrollment,
    Exam,
    ExamResult,
    Lead,
    LeadEvent,
    Lesson,
    Module,
    DayQuizQuestion,
    DayQuizResult,
    Referral,
    ReferralProfile,
    Testimonial,
    UserProfile,
)
from lms.dashboard_utils import (
    build_enrollment_dashboard_rows,
    dashboard_badge_tier,
    learning_streak_days,
)
from lms.profile_utils import (
    get_or_create_profile,
    learner_badge,
    refresh_profile_nudge_session,
)
from lms.auth_utils import (
    clear_otp_state,
    find_user_by_email,
    get_otp_state,
    record_failed_otp_attempt,
)
from lms.phone_utils import validate_whatsapp_number
from lms.services import (
    razorpay_create_order,
    razorpay_verify_enrollment_payment,
    s3_generate_presigned_url,
)


def _sanitize_tracking_metadata(meta, max_keys: int = 24, max_val_len: int = 400) -> dict:
    """Store-only safe funnel metadata (no nested structures)."""
    if not isinstance(meta, dict):
        return {}
    out = {}
    for k, v in list(meta.items())[:max_keys]:
        ks = str(k)[:64]
        if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]{0,63}$", ks):
            continue
        if isinstance(v, bool):
            out[ks] = v
        elif isinstance(v, int) and abs(v) < 2**31:
            out[ks] = v
        elif isinstance(v, float):
            out[ks] = round(v, 6)
        elif v is None:
            out[ks] = ""
        else:
            out[ks] = str(v)[:max_val_len]
    return out


def _proof_context():
    return {
        "testimonials": Testimonial.objects.filter(is_published=True)[:16],
        "case_studies": CaseStudy.objects.filter(is_published=True)[:8],
    }


def _preview_lessons_for_course(course):
    if not course:
        return []
    return list(
        Lesson.objects.filter(module__course=course, free_preview=True)
        .select_related("module")
        .order_by("module__release_day", "order", "id")[:12]
    )


class HomeView(TemplateView):
    """Landing page: hero, course overview, timeline, certificate preview, pricing, FAQ."""
    template_name = "lms/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["courses"] = (
            Course.objects.filter(is_published=True)
            .only("id", "slug", "title")
            .order_by("-created_at")[:6]
        )
        context.update(_proof_context())
        return context


class EnrollmentRequiredMixin:
    """Require that the user is enrolled in the course (course from URL)."""
    def dispatch(self, request, *args, **kwargs):
        course = self.get_course()
        slug = self.kwargs.get("slug") or (course.slug if course else None)
        if course is None:
            messages.error(request, "This course is not available.")
            return redirect("lms:course_list")
        if not request.user.is_authenticated:
            messages.info(
                request,
                "Sign in with email OTP to access your course, or enroll from the course page.",
            )
            return redirect("lms:course_detail", slug=slug)
        enrolled = Enrollment.objects.filter(
            user=request.user,
            course=course,
        ).exists()
        if not enrolled:
            messages.warning(
                request,
                "Complete payment to enroll and unlock this content.",
            )
            return redirect("lms:course_detail", slug=slug)
        return super().dispatch(request, *args, **kwargs)

    def get_course(self):
        """Override to return the Course for this request (e.g. from slug)."""
        slug = self.kwargs.get("slug")
        if not slug:
            return None
        return Course.objects.filter(slug=slug, is_published=True).first()


class SingleCoursePageView(TemplateView):
    """Courses page: when only one course, show full course detail + enroll (same as course detail page)."""
    template_name = "lms/course_detail.html"

    def get(self, request, *args, **kwargs):
        self._course = (
            Course.objects.filter(is_published=True)
            .order_by("-created_at")
            .prefetch_related(
                Prefetch(
                    "modules",
                    queryset=Module.objects.order_by("order", "release_day").prefetch_related("lessons"),
                ),
                "exams",
            )
            .first()
        )
        return super().get(request, *args, **kwargs)

    def get_template_names(self):
        if self._course is None:
            return ["lms/courses_empty.html"]
        return ["lms/course_detail.html"]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["course"] = self._course
        if self._course is None:
            return context
        if self.request.user.is_authenticated:
            context["is_enrolled"] = Enrollment.objects.filter(
                user=self.request.user,
                course=self._course,
            ).exists()
        else:
            context["is_enrolled"] = False
        if not context.get("is_enrolled"):
            context["form"] = None
        context["LMS_COURSE_PRICE_INR"] = getattr(settings, "LMS_COURSE_PRICE_INR", 2499)
        context["LMS_ORIGINAL_PRICE_INR"] = getattr(settings, "LMS_ORIGINAL_PRICE_INR", 4999)
        context["course_preview_video_url"] = getattr(
            settings, "LMS_COURSE_PREVIEW_VIDEO_URL", None
        )
        context.update(_proof_context())
        context["preview_lessons"] = _preview_lessons_for_course(self._course)
        return context


class CourseListView(ListView):
    """List published courses (used when multiple courses exist)."""
    model = Course
    context_object_name = "course_list"
    template_name = "lms/courses.html"
    paginate_by = getattr(settings, "LMS_COURSES_PER_PAGE", 12)

    def get_queryset(self):
        return (
            Course.objects.filter(is_published=True)
            .order_by("-created_at")
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        page_vid = getattr(settings, "LMS_COURSES_PAGE_VIDEO_URL", "") or ""
        preview_vid = getattr(settings, "LMS_COURSE_PREVIEW_VIDEO_URL", "") or ""
        ctx["courses_page_video_url"] = page_vid or preview_vid
        return ctx


class CourseDetailView(DetailView):
    """Course detail with modules/lessons; show enroll button if not enrolled."""
    model = Course
    context_object_name = "course"
    template_name = "lms/course_detail.html"
    slug_url_kwarg = "slug"

    def get_queryset(self):
        return (
            Course.objects.filter(is_published=True)
            .prefetch_related(
                Prefetch(
                    "modules",
                    queryset=Module.objects.order_by("order", "release_day").prefetch_related("lessons"),
                ),
                "exams",
            )
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.user.is_authenticated:
            context["is_enrolled"] = Enrollment.objects.filter(
                user=self.request.user,
                course=self.object,
            ).exists()
        else:
            context["is_enrolled"] = False
        context["form"] = None
        context["LMS_COURSE_PRICE_INR"] = getattr(settings, "LMS_COURSE_PRICE_INR", 2499)
        context["LMS_ORIGINAL_PRICE_INR"] = getattr(settings, "LMS_ORIGINAL_PRICE_INR", 4999)
        context["course_preview_video_url"] = getattr(
            settings, "LMS_COURSE_PREVIEW_VIDEO_URL", None
        )
        context.update(_proof_context())
        context["preview_lessons"] = _preview_lessons_for_course(self.object)
        return context


class EnrollView(LoginRequiredMixin, FormView):
    """Enrollment via form (used for free courses)."""
    form_class = EnrollForm
    template_name = "lms/course_detail.html"
    success_url = reverse_lazy("lms:dashboard")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        kwargs["course"] = self.get_course()
        return kwargs

    def get_course(self):
        slug = self.kwargs.get("slug")
        if not slug:
            return None
        return get_object_or_404(Course, slug=slug, is_published=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["course"] = self.get_course()
        context["is_enrolled"] = False
        return context

    def form_valid(self, form):
        course = self.get_course()
        if course and not Enrollment.objects.filter(user=self.request.user, course=course).exists():
            Enrollment.objects.create(user=self.request.user, course=course)
            refresh_profile_nudge_session(self.request)
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        slug = self.kwargs.get("slug")
        if slug:
            return reverse("lms:dashboard_course", kwargs={"slug": slug})
        return reverse("lms:dashboard")


class DashboardView(LoginRequiredMixin, ListView):
    """Unified profile + learning hub (enrollments with progress; lean queryset)."""
    model = Enrollment
    context_object_name = "enrollments"
    template_name = "lms/dashboard.html"
    paginate_by = getattr(settings, "LMS_DASHBOARD_PER_PAGE", 20)

    def get_queryset(self):
        return (
            Enrollment.objects.filter(user=self.request.user)
            .select_related("course")
            .defer("course__description", "course__thumbnail")
            .order_by("-enrolled_at")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from lms.referral_utils import get_or_create_referral_profile

        user = self.request.user
        rp = get_or_create_referral_profile(user)
        context["referral_code"] = rp.code
        context["referral_link"] = (
            f"{self.request.scheme}://{self.request.get_host()}/?ref={rp.code}"
        )
        profile = get_or_create_profile(user)
        context["learner_profile"] = profile
        context["form_section_basic"] = ProfileBasicSectionForm(
            instance=profile, prefix="sec_basic"
        )
        context["form_section_bio"] = ProfileBioSectionForm(
            instance=profile, prefix="sec_bio"
        )
        context["form_section_education"] = ProfileEducationSectionForm(
            instance=profile, prefix="sec_edu"
        )
        context["form_section_experience"] = ProfileExperienceSectionForm(
            instance=profile, prefix="sec_exp"
        )
        context["form_section_skills"] = ProfileSkillsSectionForm(
            instance=profile, prefix="sec_skills"
        )
        context["form_section_portfolio"] = ProfilePortfolioSectionForm(
            instance=profile, prefix="sec_portfolio"
        )
        context["LMS_IDENTITY_LABEL"] = getattr(
            settings, "LMS_IDENTITY_LABEL", "Learner"
        )
        certs = list(
            Certificate.objects.filter(user=user)
            .select_related("course")
            .defer("pdf_file", "course__description", "course__thumbnail")
            .order_by("-created_at")
        )
        context["user_certificates"] = certs
        context["certificate_count"] = len(certs)
        enroll_n = Enrollment.objects.filter(user=user).count()
        context["enrollment_total_count"] = enroll_n
        context["courses_completed_count"] = len(certs)
        badge_short, badge_class = dashboard_badge_tier(
            context["certificate_count"], enroll_n, profile.profile_completion
        )
        context["dashboard_badge_label"] = badge_short
        context["learner_badge_class"] = badge_class
        context["learning_streak_days"] = learning_streak_days(user)
        context["public_profile_url"] = self.request.build_absolute_uri(
            reverse("lms:public_profile", kwargs={"username": user.username})
        )
        page_obj = context.get("page_obj")
        if page_obj is not None:
            enroll_page = list(page_obj.object_list)
        else:
            enroll_page = list(context.get("enrollments", []))
        context["enrollment_rows"] = build_enrollment_dashboard_rows(user, enroll_page)
        context["show_profile_completion_modal"] = (
            profile.profile_completion < 40
            and not self.request.session.get("profile_nudge_dismissed")
        )
        return context


_DASHBOARD_SECTION_PREFIX = {
    "basic": "sec_basic",
    "bio": "sec_bio",
    "education": "sec_edu",
    "experience": "sec_exp",
    "skills": "sec_skills",
    "portfolio": "sec_portfolio",
}


class DashboardProfileAjaxView(LoginRequiredMixin, View):
    """Save one dashboard profile section per dedicated modal (JSON)."""

    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        section = (request.POST.get("profile_section") or "").strip()
        prefix = _DASHBOARD_SECTION_PREFIX.get(section)
        if not prefix:
            return JsonResponse(
                {"ok": False, "errors": {"section": ["Invalid section."]}},
                status=400,
            )
        profile = get_or_create_profile(request.user)
        form_classes = {
            "basic": ProfileBasicSectionForm,
            "bio": ProfileBioSectionForm,
            "education": ProfileEducationSectionForm,
            "experience": ProfileExperienceSectionForm,
            "skills": ProfileSkillsSectionForm,
            "portfolio": ProfilePortfolioSectionForm,
        }
        FormClass = form_classes[section]
        kwargs = {"data": request.POST, "instance": profile, "prefix": prefix}
        if section == "basic":
            kwargs["files"] = request.FILES
        form = FormClass(**kwargs)
        if form.is_valid():
            form.save()
            profile.refresh_from_db()
            return JsonResponse(
                {
                    "ok": True,
                    "section": section,
                    "profile_completion": profile.profile_completion,
                    "display_name": profile.display_name,
                    "location": profile.location or "",
                }
            )
        return JsonResponse(
            {"ok": False, "errors": {k: list(v) for k, v in form.errors.items()}},
            status=400,
        )


class DismissProfileNudgeView(LoginRequiredMixin, View):
    """Session dismiss for dashboard profile completion modal."""

    def post(self, request, *args, **kwargs):
        request.session["profile_nudge_dismissed"] = True
        next_url = request.POST.get("next") or reverse("lms:dashboard")
        if not (isinstance(next_url, str) and next_url.startswith("/") and not next_url.startswith("//")):
            next_url = reverse("lms:dashboard")
        return HttpResponseRedirect(next_url)


class PublicLearnerProfileView(View):
    """Legacy /learners/<slug>/ redirects to canonical /u/<username>/."""

    def get(self, request, *args, **kwargs):
        slug = kwargs["slug"]
        profile = (
            UserProfile.objects.select_related("user")
            .filter(public_slug=slug)
            .first()
        )
        if not profile or not profile.is_public:
            raise Http404()
        return HttpResponsePermanentRedirect(
            reverse("lms:public_profile", kwargs={"username": profile.user.username}),
        )


class PublicProfileView(TemplateView):
    """Shareable student portfolio at /u/<username>/ (no login)."""

    template_name = "lms/public_profile.html"

    def dispatch(self, request, *args, **kwargs):
        User = get_user_model()
        username = kwargs.get("username") or ""
        self.profile_user = get_object_or_404(User, username=username)
        self.student_profile = (
            UserProfile.objects.select_related("user")
            .filter(user=self.profile_user)
            .first()
        )
        if not self.student_profile:
            raise Http404()
        if not self.student_profile.is_public:
            raise Http404()
        if not Enrollment.objects.filter(user=self.profile_user).exists():
            raise Http404()
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        p = self.student_profile
        u = self.profile_user
        identity = getattr(settings, "LMS_IDENTITY_LABEL", "Learner")
        certs = list(
            Certificate.objects.filter(user=u)
            .select_related("course")
            .defer("pdf_file", "course__description", "course__thumbnail")
            .order_by("-created_at")
        )
        enroll_n = Enrollment.objects.filter(user=u).count()
        badge_label, badge_class = learner_badge(len(certs), enroll_n, p.profile_completion)
        share_url = self.request.build_absolute_uri(
            reverse("lms:public_profile", kwargs={"username": u.username})
        )
        name = p.display_name
        nav_initial = (name.strip()[:1] or u.username[:1] or "?").upper()
        og_image = ""
        if p.profile_photo:
            try:
                og_image = self.request.build_absolute_uri(p.profile_photo.url)
            except Exception:
                og_image = ""
        ctx.update(
            {
                "portfolio_og_image": og_image,
                "student_profile": p,
                "profile_user": u,
                "learner_profile": p,
                "display_skills": p.skills_list[:28],
                "LMS_IDENTITY_LABEL": identity,
                "public_certificates": certs,
                "first_certificate": certs[0] if certs else None,
                "learner_badge_label": badge_label,
                "learner_badge_class": badge_class,
                "portfolio_share_url": share_url,
                "portfolio_meta_title": f"{name} | {identity} Profile | BThinkX",
                "portfolio_meta_description": (
                    f"View {name}'s {identity} portfolio and verified achievements on BThinkX."
                ),
                "whatsapp_contact_url": self._whatsapp_contact_url(p),
                "email_contact_href": self._mailto_contact(p, u),
                "learning_highlights": self._learning_highlights(certs),
                "completed_program_label": (
                    f"Completed {certs[0].course.title} program"
                    if certs
                    else None
                ),
                "portfolio_nav_initial": nav_initial,
            }
        )
        return ctx

    @staticmethod
    def _whatsapp_contact_url(p):
        if not p.public_whatsapp_contact or not (p.phone or "").strip():
            return ""
        from lms.phone_utils import normalize_whatsapp_digits

        d = normalize_whatsapp_digits(p.phone)
        if len(d) < 10:
            return ""
        return f"https://wa.me/{d}"

    @staticmethod
    def _mailto_contact(p, u):
        if not p.public_email_contact or not (u.email or "").strip():
            return ""
        return "mailto:{}?subject={}".format(u.email, quote("Hello via your BThinkX portfolio"))

    @staticmethod
    def _learning_highlights(certs):
        out = []
        for cert in certs[:6]:
            raw = strip_tags(cert.course.description or "")
            raw = " ".join(raw.split())
            excerpt = (
                (raw[:200].rsplit(" ", 1)[0] + "…")
                if len(raw) > 200
                else (raw or "Verified completion with proctored-style assessment.")
            )
            out.append(
                {
                    "course_title": cert.course.title,
                    "excerpt": excerpt,
                    "completed_at": cert.created_at,
                    "certificate_id": cert.certificate_id,
                }
            )
        return out


class DashboardCourseDetailView(LoginRequiredMixin, EnrollmentRequiredMixin, DetailView):
    """Dashboard course detail: modules, lessons, locked/unlocked, exam status, certificate."""
    model = Course
    context_object_name = "course"
    template_name = "lms/dashboard_course.html"
    slug_url_kwarg = "slug"

    def get_queryset(self):
        return (
            Course.objects.filter(is_published=True)
            .prefetch_related(
                Prefetch(
                    "modules",
                    queryset=Module.objects.order_by("order", "release_day").prefetch_related("lessons"),
                ),
                "exams",
            )
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        enrollment = (
            Enrollment.objects.filter(user=user, course=self.object)
            .order_by("-enrolled_at")
            .first()
        )
        context["enrollment"] = enrollment
        exam_results = {
            r.exam_id: r
            for r in ExamResult.objects.filter(
                user=user,
                exam__course=self.object,
            ).select_related("exam")
        }
        context["exams_with_results"] = [
            (exam, exam_results.get(exam.id))
            for exam in self.object.exams.filter(is_published=True)
        ]
        context["certificate"] = (
            Certificate.objects.filter(user=user, course=self.object).first()
        )
        unlocked_lesson_ids = set()
        lesson_unlock_messages = {}
        for module in self.object.modules.all():
            for lesson in module.lessons.all():
                if lesson.is_unlocked(user):
                    unlocked_lesson_ids.add(lesson.pk)
                else:
                    day = lesson.get_release_day()
                    if day > 1:
                        lesson_unlock_messages[lesson.pk] = f"Complete Day {day-1} quiz with at least 6/10 to unlock."
                    else:
                        lesson_unlock_messages[lesson.pk] = "This lesson is locked."
        context["unlocked_lesson_ids"] = unlocked_lesson_ids
        context["lesson_unlock_messages"] = lesson_unlock_messages

        total_lessons = Lesson.objects.filter(module__course=self.object).count()
        n_unlocked = len(unlocked_lesson_ids)
        context["total_lessons"] = total_lessons
        context["completed_lessons"] = (
            int(round(100 * n_unlocked / total_lessons)) if total_lessons else 0
        )

        passed_days = set(
            DayQuizResult.objects.filter(
                user=user,
                module__course=self.object,
                passed=True,
            ).values_list("module__release_day", flat=True)
        )
        context["passed_quiz_days"] = passed_days
        streak = 0
        for d in range(1, 32):
            if d in passed_days:
                streak += 1
            else:
                break
        context["day_streak"] = streak

        next_url = None
        next_label = None
        for m in self.object.modules.all().order_by("release_day", "order"):
            if m.release_day >= 7:
                break
            if not DayQuizResult.objects.filter(
                user=user, module=m, passed=True
            ).exists():
                next_url = reverse(
                    "lms:day_quiz",
                    kwargs={"slug": self.object.slug, "day": m.release_day},
                )
                next_label = f"Continue Day {m.release_day}: unlock next lessons"
                break
        if next_url is None:
            ex = self.object.exams.filter(is_published=True).first()
            if ex:
                next_url = reverse(
                    "lms:exam_detail",
                    kwargs={"slug": self.object.slug, "exam_slug": ex.slug},
                )
                next_label = "Take the final exam to earn your certificate"
        context["next_action_url"] = next_url
        context["next_action_label"] = next_label

        demo_key = getattr(settings, "LMS_DEMO_VIDEO_KEY", "")
        if demo_key:
            context["demo_video_url"] = s3_generate_presigned_url(demo_key)
        else:
            context["demo_video_url"] = None
        return context


class DayQuizView(LoginRequiredMixin, EnrollmentRequiredMixin, TemplateView):
    """
    Per-day quiz view: 10 questions, 4 options, 1 mark each.
    Requires score >= 6 to unlock the next day.
    """
    template_name = "lms/day_quiz.html"

    def get_module(self):
        course = self.get_course()
        day = int(self.kwargs.get("day"))
        return get_object_or_404(
            Module,
            course=course,
            release_day=day,
        )

    def get_course(self):
        slug = self.kwargs.get("slug")
        return get_object_or_404(Course, slug=slug, is_published=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        module = self.get_module()
        questions = list(module.day_quiz_questions.all().order_by("order", "id")[:10])
        context["course"] = module.course
        context["module"] = module
        context["questions"] = questions
        existing = DayQuizResult.objects.filter(
            user=self.request.user,
            module=module,
        ).order_by("-submitted_at").first()
        context["existing_result"] = existing
        return context

    def post(self, request, *args, **kwargs):
        module = self.get_module()
        questions = list(module.day_quiz_questions.all().order_by("order", "id")[:10])
        score = 0
        for q in questions:
            key = f"q_{q.id}"
            try:
                selected = int(request.POST.get(key, "0"))
            except ValueError:
                selected = 0
            if selected == q.correct_option:
                score += 1
        result, _created = DayQuizResult.objects.get_or_create(
            user=request.user,
            module=module,
            defaults={"score": score},
        )
        if not _created:
            result.score = score
        result.save()
        context = self.get_context_data()
        context["just_submitted"] = True
        context["score"] = score
        return self.render_to_response(context)


class LessonView(DetailView):
    """Single lesson: video (presigned URL); redirects if locked or not enrolled."""
    model = Lesson
    context_object_name = "lesson"
    template_name = "lms/lesson.html"
    pk_url_kwarg = "lesson_id"

    def get_queryset(self):
        return Lesson.objects.select_related("module", "module__course")

    def dispatch(self, request, *args, **kwargs):
        slug = self.kwargs.get("slug")
        lesson_id = self.kwargs.get("lesson_id")
        lesson = (
            Lesson.objects.filter(pk=lesson_id, module__course__slug=slug)
            .select_related("module", "module__course")
            .first()
        )
        if lesson is None:
            messages.error(request, "Lesson not found.")
            return redirect("lms:dashboard") if request.user.is_authenticated else redirect("lms:course_list")
        course = lesson.module.course
        if not request.user.is_authenticated:
            if lesson.free_preview:
                return redirect(
                    "lms:lesson_preview",
                    slug=course.slug,
                    lesson_id=lesson.pk,
                )
            messages.info(request, "Sign in to watch lessons.")
            return redirect("lms:course_detail", slug=course.slug)
        if not Enrollment.objects.filter(user=request.user, course=course).exists():
            if lesson.free_preview:
                return redirect(
                    "lms:lesson_preview",
                    slug=course.slug,
                    lesson_id=lesson.pk,
                )
            messages.warning(request, "Enroll in the course to access this lesson.")
            return redirect("lms:course_detail", slug=course.slug)
        if not lesson.is_unlocked(request.user):
            day = lesson.get_release_day()
            if day > 1:
                messages.info(
                    request,
                    f"Complete the Day {day - 1} quiz with at least 6/10 to unlock this lesson.",
                )
            else:
                messages.info(
                    request,
                    "Complete the previous day's quiz to unlock this lesson.",
                )
            return redirect("lms:dashboard_course", slug=course.slug)
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        qs = queryset or self.get_queryset()
        qs = qs.filter(module__course__slug=self.kwargs.get("slug"))
        return get_object_or_404(qs, pk=self.kwargs.get("lesson_id"))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["course"] = self.object.module.course
        context["module"] = self.object.module
        expiry = getattr(settings, "LMS_S3_PRESIGNED_EXPIRY", 300)
        # Demo S3 video for dashboard/lessons (use a shared demo key)
        demo_key = getattr(settings, "LMS_DEMO_VIDEO_KEY", "") or self.object.video_key
        if demo_key:
            from lms.services import s3_generate_presigned_url
            context["video_url"] = s3_generate_presigned_url(demo_key, expiry_seconds=expiry)
        else:
            context["video_url"] = None
        return context


class PreviewLessonView(DetailView):
    """Public free-preview lesson (no login or enrollment)."""

    model = Lesson
    context_object_name = "lesson"
    template_name = "lms/lesson_preview.html"
    pk_url_kwarg = "lesson_id"

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        if not self.object.free_preview:
            return redirect("lms:course_detail", slug=self.kwargs["slug"])
        return super().get(request, *args, **kwargs)

    def get_object(self, queryset=None):
        return get_object_or_404(
            Lesson.objects.filter(
                free_preview=True,
                module__course__slug=self.kwargs["slug"],
                module__course__is_published=True,
            ).select_related("module", "module__course"),
            pk=self.kwargs["lesson_id"],
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["course"] = self.object.module.course
        context["module"] = self.object.module
        context["is_free_preview"] = True
        expiry = getattr(settings, "LMS_S3_PRESIGNED_EXPIRY", 300)
        demo_key = getattr(settings, "LMS_DEMO_VIDEO_KEY", "") or self.object.video_key
        if demo_key:
            context["video_url"] = s3_generate_presigned_url(demo_key, expiry_seconds=expiry)
        else:
            context["video_url"] = None
        return context


class CertificateDownloadView(LoginRequiredMixin, View):
    """Serve certificate PDF if user owns the certificate."""
    def get(self, request, certificate_id):
        cert = get_object_or_404(
            Certificate.objects.select_related("user", "course"),
            certificate_id=certificate_id,
        )
        if cert.user_id != request.user.id:
            return HttpResponseForbidden()
        if not cert.pdf_file:
            from lms.services import certificate_generate_pdf
            if not certificate_generate_pdf(cert):
                return HttpResponseForbidden("Certificate PDF not available.")
            cert.refresh_from_db()
        if not cert.pdf_file:
            return HttpResponseForbidden("Certificate PDF not available.")
        try:
            from django.http import FileResponse
            return FileResponse(
                cert.pdf_file.open("rb"),
                as_attachment=True,
                filename=f"certificate_{cert.certificate_id}.pdf",
            )
        except (ValueError, OSError):
            return HttpResponseForbidden("File not available.")


class ExamDetailView(LoginRequiredMixin, EnrollmentRequiredMixin, DetailView):
    """Exam detail: instructions, result if admin uploaded score."""
    model = Exam
    context_object_name = "exam"
    template_name = "lms/exam.html"
    slug_url_kwarg = "exam_slug"

    def get_queryset(self):
        return Exam.objects.filter(
            course__slug=self.kwargs.get("slug"),
            course__is_published=True,
            is_published=True,
        ).select_related("course")

    def get_object(self, queryset=None):
        qs = queryset or self.get_queryset()
        return get_object_or_404(qs, slug=self.kwargs.get("exam_slug"))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["course"] = self.object.course
        context["result"] = (
            ExamResult.objects.filter(
                exam=self.object,
                user=self.request.user,
            ).first()
        )
        context["certificate"] = (
            Certificate.objects.filter(
                user=self.request.user,
                course=self.object.course,
            ).first()
        )
        return context


class CertificateDetailView(LoginRequiredMixin, TemplateView):
    """View certificate (owned by user) with QR and download."""
    template_name = "lms/certificate.html"

    def dispatch(self, request, *args, **kwargs):
        cert_id = self.kwargs.get("certificate_id")
        if not cert_id:
            return HttpResponseForbidden()
        cert = Certificate.objects.filter(
            certificate_id=cert_id,
            user=request.user,
        ).select_related("user", "course").first()
        if cert is None:
            return HttpResponseForbidden("Certificate not found.")
        self.certificate = cert
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["certificate"] = self.certificate
        context["qr_data"] = None
        verify_path = reverse(
            "lms:verify",
            kwargs={"certificate_id": self.certificate.certificate_id},
        )
        context["certificate_public_url"] = self.request.build_absolute_uri(verify_path)
        from urllib.parse import quote_plus

        context["linkedin_share_url"] = (
            "https://www.linkedin.com/sharing/share-offsite/?url="
            + quote_plus(context["certificate_public_url"])
        )
        try:
            from lms.services import certificate_generate_qr_code
            qr_bytes = certificate_generate_qr_code(self.certificate)
            if qr_bytes:
                import base64
                context["qr_data"] = base64.b64encode(qr_bytes).decode("ascii")
        except Exception:
            pass
        return context


class RegisterView(CreateView):
    """User registration."""
    form_class = RegisterForm
    template_name = "lms/register.html"
    success_url = reverse_lazy("lms:dashboard")

    def form_valid(self, form):
        user = form.save()
        self.request.session.cycle_key()
        login(self.request, user)
        return HttpResponseRedirect(self.get_success_url())


class LoginRequestOTPView(View):
    """Start email-based login/signup by emailing a one-time code."""

    def post(self, request, *args, **kwargs):
        from django.conf import settings as dj_settings
        from lms.auth_utils import (
            clear_otp_state,
            generate_otp_code,
            store_otp_in_session,
        )

        logger = logging.getLogger("lms.otp")
        email = (request.POST.get("email") or "").strip()
        if not email:
            return JsonResponse(
                {"ok": False, "error": "Please enter your email address."},
                status=400,
            )

        if not (dj_settings.EMAIL_HOST_USER and dj_settings.EMAIL_HOST_PASSWORD):
            logger.error("OTP requested but EMAIL_HOST_USER / EMAIL_HOST_PASSWORD not configured.")
            return JsonResponse(
                {
                    "ok": False,
                    "error": "Sign-in by email is temporarily unavailable. Please contact support.",
                },
                status=503,
            )

        ttl = 10
        code = generate_otp_code()
        subject = getattr(dj_settings, "LMS_OTP_EMAIL_SUBJECT", "Your BThinkX sign-in code")
        from lms.emailing import send_branded_email_safe

        if not send_branded_email_safe(
            subject=subject,
            template_name="otp_login",
            to_emails=[email],
            context={"code": code, "ttl_minutes": ttl},
            request=request,
        ):
            return JsonResponse(
                {
                    "ok": False,
                    "error": "We could not send the email. Check the address and try again in a moment.",
                },
                status=502,
            )

        clear_otp_state(request.session)
        store_otp_in_session(request.session, email=email, code=code, ttl_minutes=ttl)
        return JsonResponse(
            {
                "ok": True,
                "message": "We've sent a one-time code to your email.",
            }
        )


class LoginVerifyOTPView(View):
    """Verify an email + OTP combination, logging in or creating a user."""

    def post(self, request, *args, **kwargs):
        email = (request.POST.get("email") or "").strip()
        code = (request.POST.get("code") or "").strip()

        if not email or not code:
            return JsonResponse(
                {"ok": False, "error": "Please enter both email and code."},
                status=400,
            )

        state = get_otp_state(request.session)
        if not state or state.email.lower() != email.lower():
            return JsonResponse(
                {
                    "ok": False,
                    "error": "No active code for this email. Please request a new code.",
                },
                status=400,
            )

        from django.utils import timezone

        now = timezone.now()
        if now > state.expires_at:
            clear_otp_state(request.session)
            return JsonResponse(
                {"ok": False, "error": "This code has expired. Please request a new one."},
                status=400,
            )

        if code != state.code:
            return JsonResponse(
                {"ok": False, "error": "The code you entered is incorrect."},
                status=400,
            )

        user = find_user_by_email(email)
        if not user:
            # Auto-create a user for this email (signup-on-first-login).
            User = get_user_model()
            base_username = email.split("@")[0] or "user"
            candidate = base_username
            counter = 1
            while User.objects.filter(username=candidate).exists():
                counter += 1
                candidate = f"{base_username}{counter}"
            user = User(username=candidate, email=email)
            user.set_unusable_password()
            user.save()

        clear_otp_state(request.session)
        request.session.cycle_key()
        login(request, user)
        logging.getLogger("lms.otp").info("otp_login_success user_id=%s", user.pk)
        from django.middleware.csrf import get_token

        return JsonResponse({"ok": True, "csrfToken": get_token(request)})


class RazorpayCreateOrderView(LoginRequiredMixin, View):
    """
    Create a Razorpay order for the single course.
    Returns JSON with order details for Checkout.js.
    """

    def post(self, request, *args, **kwargs):
        slug = self.kwargs.get("slug")
        course = get_object_or_404(Course, slug=slug, is_published=True)
        price_rupees = course.price if course.price is not None and course.price > 0 else getattr(
            settings, "LMS_COURSE_PRICE_INR", 2499
        )
        try:
            amount_paise = int(price_rupees * 100)
        except TypeError:
            amount_paise = int(getattr(settings, "LMS_COURSE_PRICE_INR", 2499) * 100)

        ref_code = (request.session.get("referral_code") or "").strip()
        discount_pct = int(getattr(settings, "LMS_REFERRAL_DISCOUNT_PERCENT", 0) or 0)
        request.session.pop("referral_code_active", None)
        request.session.pop("referral_discount_applied", None)
        if ref_code and 0 < discount_pct < 100:
            prof = (
                ReferralProfile.objects.filter(code__iexact=ref_code)
                .exclude(user_id=request.user.id)
                .first()
            )
            if prof:
                amount_paise = max(100, int(amount_paise * (100 - discount_pct) / 100))
                request.session["referral_code_active"] = ref_code
                request.session["referral_discount_applied"] = discount_pct

        order = razorpay_create_order(
            amount_paise=amount_paise,
            receipt=f"course-{course.id}-user-{request.user.id}",
            notes={
                "course_slug": str(course.slug)[:255],
                "user_id": str(request.user.id),
                "expected_amount_paise": str(int(amount_paise)),
            },
        )
        if not order:
            return JsonResponse(
                {"ok": False, "error": "Unable to start payment. Please try again."},
                status=500,
            )

        return JsonResponse(
            {
                "ok": True,
                "order_id": order.get("id"),
                "amount": order.get("amount"),
                "currency": order.get("currency"),
                "key_id": settings.RZP_CLIENT_ID,
                "course_title": course.title,
                "user_email": request.user.email,
                "user_name": getattr(request.user, "get_full_name", lambda: "")() or request.user.username,
            }
        )


class RazorpayVerifyPaymentView(LoginRequiredMixin, View):
    """
    Verify Razorpay payment signature and create Enrollment on success.
    Intended to be called from the Checkout.js handler.
    """

    def post(self, request, *args, **kwargs):
        order_id = (request.POST.get("razorpay_order_id") or "").strip()
        payment_id = (request.POST.get("razorpay_payment_id") or "").strip()
        signature = (request.POST.get("razorpay_signature") or "").strip()
        slug = (request.POST.get("slug") or "").strip()

        if not order_id or not payment_id or not signature or not slug:
            return JsonResponse(
                {"ok": False, "error": "Missing payment details."},
                status=400,
            )

        pay_log = logging.getLogger("lms.payments")
        ok_pay, pay_err = razorpay_verify_enrollment_payment(
            order_id,
            payment_id,
            signature,
            course_slug=slug,
            user_id=request.user.id,
        )
        if not ok_pay:
            pay_log.warning(
                "razorpay_verify_failed user_id=%s slug=%s err=%s",
                request.user.id,
                slug,
                pay_err,
            )
            return JsonResponse(
                {
                    "ok": False,
                    "error": "Payment verification failed. If you were charged, contact support with your payment ID.",
                },
                status=400,
            )

        course = get_object_or_404(Course, slug=slug, is_published=True)
        enrollment, created = Enrollment.objects.get_or_create(
            user=request.user,
            course=course,
        )
        if created:
            pay_log.info(
                "enrollment_created user_id=%s course=%s payment_id=%s",
                request.user.id,
                course.slug,
                payment_id[:24] if payment_id else "",
            )
            refresh_profile_nudge_session(request)
        redirect_url = reverse("lms:dashboard_course", kwargs={"slug": course.slug})

        ref_code = (request.session.pop("referral_code_active", None) or "").strip()
        discount_pct = int(request.session.pop("referral_discount_applied", 0) or 0)
        if ref_code and created:
            prof = ReferralProfile.objects.filter(code__iexact=ref_code).first()
            if prof and prof.user_id != request.user.id:
                Referral.objects.get_or_create(
                    referred_user=request.user,
                    course=course,
                    defaults={
                        "referrer": prof.user,
                        "reward_status": Referral.RewardStatus.PENDING,
                        "discount_percent_used": discount_pct,
                    },
                )

        upsell = None
        if getattr(settings, "LMS_POST_PURCHASE_UPSELL_TITLE", ""):
            upsell = {
                "title": settings.LMS_POST_PURCHASE_UPSELL_TITLE,
                "body": getattr(settings, "LMS_POST_PURCHASE_UPSELL_BODY", ""),
                "cta_url": getattr(settings, "LMS_POST_PURCHASE_UPSELL_URL", "/"),
                "cta_label": getattr(settings, "LMS_POST_PURCHASE_UPSELL_CTA", "Learn more"),
            }
        return JsonResponse(
            {"ok": True, "redirect_url": redirect_url, "upsell": upsell}
        )


class LeadCaptureView(View):
    """
    AJAX/JSON lead capture. CSRF required (cookie + header).
    """

    http_method_names = ["post", "options"]

    def post(self, request, *args, **kwargs):
        variant = (request.COOKIES.get("lms_ab") or "a")[:8]
        if request.content_type and "application/json" in request.content_type:
            try:
                body = json.loads(request.body.decode() or "{}")
            except json.JSONDecodeError:
                return JsonResponse({"ok": False, "error": "Invalid JSON."}, status=400)
            email = (body.get("email") or "").strip()
            name = (body.get("name") or "").strip()[:255]
            phone = (body.get("phone") or "").strip()[:32]
            source = (body.get("source") or "web").strip()[:64]
            variant = (body.get("variant") or variant)[:8]
        else:
            email = (request.POST.get("email") or "").strip()
            name = (request.POST.get("name") or "").strip()[:255]
            phone = (request.POST.get("phone") or "").strip()[:32]
            source = (request.POST.get("source") or "web").strip()[:64]

        phone_ok, phone_err = validate_whatsapp_number(phone)
        if not phone_ok:
            return JsonResponse({"ok": False, "error": phone_err}, status=400)
        if email:
            from django.core.exceptions import ValidationError
            from django.core.validators import validate_email

            try:
                validate_email(email)
            except ValidationError:
                return JsonResponse(
                    {"ok": False, "error": "Please enter a valid email or leave it blank."},
                    status=400,
                )
        lead = Lead.objects.create(
            email=email,
            name=name,
            phone=phone_ok,
            source=source,
            variant=variant,
        )
        logging.getLogger("lms.leads").info(
            "lead_capture id=%s source=%s", lead.pk, source[:64]
        )
        magnet = getattr(settings, "LMS_LEAD_MAGNET_PDF_URL", "") or ""
        if email:
            msg_ok = (
                "You're on the list. Check your inbox soon."
                if not magnet
                else "Success! Opening your resource…"
            )
        else:
            msg_ok = (
                "Thanks! We’ll send the prompt pack to your WhatsApp."
                if not magnet
                else "Success! Check WhatsApp, opening your resource…"
            )
        return JsonResponse(
            {
                "ok": True,
                "lead_id": lead.pk,
                "magnet_url": magnet or None,
                "message": msg_ok,
            }
        )


class TrackLeadEventView(View):
    """Record funnel events (pricing view, checkout abandon, etc.)."""

    http_method_names = ["post", "options"]

    ALLOWED = frozenset(
        {
            LeadEvent.EventType.VIEWED_PRICING.value,
            LeadEvent.EventType.CHECKOUT_STARTED.value,
            LeadEvent.EventType.CHECKOUT_ABANDONED.value,
        }
    )

    def post(self, request, *args, **kwargs):
        try:
            body = json.loads(request.body.decode() or "{}")
        except json.JSONDecodeError:
            return JsonResponse({"ok": False, "error": "Invalid JSON."}, status=400)
        et = (body.get("event_type") or "").strip()
        if et not in self.ALLOWED:
            return JsonResponse({"ok": False, "error": "Invalid event."}, status=400)
        lead_id_raw = body.get("lead_id")
        email = (body.get("email") or "").strip()[:254]
        lead = None
        if lead_id_raw is not None and lead_id_raw != "":
            try:
                lid = int(lead_id_raw)
                if lid > 0:
                    lead = Lead.objects.filter(pk=lid).first()
            except (ValueError, TypeError):
                pass
        if lead is None and email:
            lead = Lead.objects.filter(email__iexact=email).order_by("-id").first()
        user = request.user if request.user.is_authenticated else None
        raw_meta = body.get("meta") if isinstance(body.get("meta"), dict) else None
        if raw_meta is None and isinstance(body.get("metadata"), dict):
            raw_meta = body.get("metadata")
        meta = _sanitize_tracking_metadata(raw_meta or {})
        LeadEvent.objects.create(
            lead=lead,
            user=user,
            event_type=et,
            metadata=meta,
        )
        try:
            from lms.followup import notify_lead_pipeline

            notify_lead_pipeline(
                et,
                lead=lead,
                user=user,
                email=email or (lead.email if lead else ""),
            )
        except Exception:
            pass
        return JsonResponse({"ok": True})


class ActivityFeedView(View):
    """Public JSON list of recent activity lines for live social-proof toasts."""

    def get(self, request, *args, **kwargs):
        if not getattr(settings, "LMS_LIVE_ACTIVITY_ENABLED", True):
            return JsonResponse({"messages": [], "enabled": False})
        from lms.activity_messages import fallback_demo_messages

        qs = ActivityEvent.objects.order_by("-created_at")[:100]
        messages = list(qs.values_list("message", flat=True))
        if not messages and getattr(settings, "LMS_LIVE_ACTIVITY_FALLBACK", False):
            messages = fallback_demo_messages(6)
        return JsonResponse({"messages": messages, "enabled": True})


class SetReferralSessionView(View):
    """Store ?ref= code in session for checkout discount + attribution."""

    http_method_names = ["post", "options"]

    def post(self, request, *args, **kwargs):
        try:
            body = json.loads(request.body.decode() or "{}")
        except json.JSONDecodeError:
            body = {}
        code = (body.get("code") or request.POST.get("code") or "").strip().upper()
        if not re.match(r"^[A-Z0-9]{4,16}$", code):
            return JsonResponse(
                {"ok": False, "error": "Invalid referral code format."},
                status=400,
            )
        if ReferralProfile.objects.filter(code__iexact=code).exists():
            request.session["referral_code"] = code
            return JsonResponse({"ok": True})
        return JsonResponse({"ok": False, "error": "Invalid code."}, status=400)


class VerifyIndexView(TemplateView):
    """Landing page for certificate verification with form to enter ID."""
    template_name = "lms/verify_index.html"

    def post(self, request, *args, **kwargs):
        cert_id = (request.POST.get("certificate_id") or "").strip()
        if cert_id:
            return redirect("lms:verify", certificate_id=cert_id)
        return self.get(request, *args, **kwargs)


class VerifyCertificateView(TemplateView):
    """Public verification page for certificate_id."""
    template_name = "lms/verify.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        raw = (self.kwargs.get("certificate_id") or "").strip()
        if len(raw) > 40 or not re.match(r"^[A-Za-z0-9\-]+$", raw):
            context["certificate_id"] = raw[:80] if raw else ""
            context["certificate"] = None
            return context
        cert_id = raw
        context["certificate_id"] = cert_id
        context["certificate"] = (
            Certificate.objects.filter(certificate_id=cert_id)
            .select_related("user", "course")
            .first()
        )
        return context
