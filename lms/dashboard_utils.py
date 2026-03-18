"""
Reusable dashboard metrics: learning streak, per-enrollment progress, badge labels.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import timedelta

from django.db.models import Count
from django.db.models.functions import TruncDate
from django.urls import reverse
from django.utils import timezone

from lms.models import Certificate, DayQuizResult, Lesson, Module
from lms.profile_utils import learner_badge


def learning_streak_days(user) -> int:
    """
    Consecutive calendar days with at least one passed day-quiz, anchored at the
    most recent activity day (streak breaks if gap > 1 day from today).
    """
    if not user or not getattr(user, "is_authenticated", False):
        return 0
    dates = set(
        DayQuizResult.objects.filter(user=user, passed=True)
        .annotate(d=TruncDate("submitted_at"))
        .values_list("d", flat=True)
        .distinct()
    )
    if not dates:
        return 0
    today = timezone.now().date()
    anchor = today if today in dates else today - timedelta(days=1)
    if anchor not in dates:
        last = max(d for d in dates if d <= today) if dates else None
        if last is None or (today - last).days > 1:
            return 0
        anchor = last
    streak = 0
    d = anchor
    while d in dates:
        streak += 1
        d -= timedelta(days=1)
    return streak


def _lesson_progress_pct_by_course(user, course_ids: list[int]) -> dict[int, int]:
    """
    Same metric as DashboardCourseDetailView.completed_lessons:
    round(100 * unlocked_lessons / total_lessons) per course.
    """
    if not course_ids:
        return {}
    course_ids = list(dict.fromkeys(course_ids))

    totals = dict(
        Lesson.objects.filter(module__course_id__in=course_ids)
        .values("module__course_id")
        .annotate(c=Count("id"))
        .values_list("module__course_id", "c")
    )

    modules_by_course: dict[int, list] = defaultdict(list)
    for m in Module.objects.filter(course_id__in=course_ids).order_by(
        "release_day", "order", "id"
    ):
        modules_by_course[m.course_id].append(m)

    passed_mods: dict[int, set] = defaultdict(set)
    for cid, mid in DayQuizResult.objects.filter(
        user=user, passed=True, module__course_id__in=course_ids
    ).values_list("module__course_id", "module_id"):
        passed_mods[cid].add(mid)

    unlocked: dict[int, int] = defaultdict(int)
    for lesson in Lesson.objects.filter(module__course_id__in=course_ids).select_related(
        "module"
    ):
        cid = lesson.module.course_id
        d = lesson.module.release_day
        day_first = {}
        for mod in modules_by_course[cid]:
            if mod.release_day not in day_first:
                day_first[mod.release_day] = mod
        if d <= 1:
            unlocked[cid] += 1
            continue
        prev = day_first.get(d - 1)
        if prev is None or prev.id in passed_mods[cid]:
            unlocked[cid] += 1

    out: dict[int, int] = {}
    for cid in course_ids:
        t = totals.get(cid) or 0
        u = unlocked.get(cid, 0)
        out[cid] = int(round(100 * u / t)) if t else 0
    return out


def build_enrollment_dashboard_rows(user, enrollments_list: list) -> list[dict]:
    """
    For each enrollment: progress % (unlocked lessons / total lessons; same as
    course dashboard), status, continue URL.
    """
    if not enrollments_list:
        return []
    course_ids = [e.course_id for e in enrollments_list]
    cert_course_ids = set(
        Certificate.objects.filter(user=user, course_id__in=course_ids).values_list(
            "course_id", flat=True
        )
    )
    progress_by_course = _lesson_progress_pct_by_course(user, course_ids)
    rows = []
    for e in enrollments_list:
        cid = e.course_id
        progress = progress_by_course.get(cid, 0)
        if cid in cert_course_ids:
            status = "Completed"
        else:
            status = "In Progress"
        rows.append(
            {
                "enrollment": e,
                "course": e.course,
                "progress_pct": progress,
                "status": status,
                "continue_url": reverse(
                    "lms:dashboard_course", kwargs={"slug": e.course.slug}
                ),
            }
        )
    return rows


def dashboard_badge_tier(cert_count: int, enrollment_count: int, completion: int) -> tuple[str, str]:
    """Returns short label (Beginner | Active | Pro) and CSS class."""
    label, css = learner_badge(cert_count, enrollment_count, completion)
    if "Pro" in label:
        return "Pro", css
    if "Active" in label:
        return "Active", css
    return "Beginner", css
