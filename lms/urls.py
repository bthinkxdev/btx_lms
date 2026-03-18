"""
LMS URL configuration.
"""
from django.urls import path
from django.views.generic import RedirectView

from lms import views

app_name = "lms"

urlpatterns = [
    path("", views.HomeView.as_view(), name="home"),
    path("courses/", views.SingleCoursePageView.as_view(), name="course_list"),
    path("courses/<slug:slug>/", views.CourseDetailView.as_view(), name="course_detail"),
    path(
        "courses/<slug:slug>/preview/<int:lesson_id>/",
        views.PreviewLessonView.as_view(),
        name="lesson_preview",
    ),
    path("courses/<slug:slug>/enroll/", views.EnrollView.as_view(), name="enroll"),
    path(
        "courses/<slug:slug>/create-order/",
        views.RazorpayCreateOrderView.as_view(),
        name="razorpay_create_order",
    ),
    path("register/", views.RegisterView.as_view(), name="register"),
    path(
        "payments/razorpay/verify/",
        views.RazorpayVerifyPaymentView.as_view(),
        name="razorpay_verify_payment",
    ),
    path("auth/request-otp/", views.LoginRequestOTPView.as_view(), name="login_request_otp"),
    path("auth/verify-otp/", views.LoginVerifyOTPView.as_view(), name="login_verify_otp"),
    path("api/leads/", views.LeadCaptureView.as_view(), name="lead_capture"),
    path("api/track/", views.TrackLeadEventView.as_view(), name="track_event"),
    path(
        "api/activity-feed/",
        views.ActivityFeedView.as_view(),
        name="activity_feed",
    ),
    path("api/ref/session/", views.SetReferralSessionView.as_view(), name="ref_session"),
    path("dashboard/", views.DashboardView.as_view(), name="dashboard"),
    path(
        "dashboard/profile/save/",
        views.DashboardProfileAjaxView.as_view(),
        name="dashboard_profile_save",
    ),
    path(
        "dashboard/profile/",
        RedirectView.as_view(pattern_name="lms:dashboard", permanent=False),
        name="profile_edit",
    ),
    path(
        "dashboard/profile/dismiss-nudge/",
        views.DismissProfileNudgeView.as_view(),
        name="profile_dismiss_nudge",
    ),
    path(
        "u/<str:username>/",
        views.PublicProfileView.as_view(),
        name="public_profile",
    ),
    path(
        "learners/<slug:slug>/",
        views.PublicLearnerProfileView.as_view(),
        name="learner_public",
    ),
    path(
        "dashboard/course/<slug:slug>/",
        views.DashboardCourseDetailView.as_view(),
        name="dashboard_course",
    ),
    path(
        "dashboard/course/<slug:slug>/day/<int:day>/quiz/",
        views.DayQuizView.as_view(),
        name="day_quiz",
    ),
    path(
        "dashboard/course/<slug:slug>/lesson/<int:lesson_id>/",
        views.LessonView.as_view(),
        name="lesson",
    ),
    path(
        "dashboard/course/<slug:slug>/exam/<slug:exam_slug>/",
        views.ExamDetailView.as_view(),
        name="exam_detail",
    ),
    path(
        "certificate/<str:certificate_id>/",
        views.CertificateDetailView.as_view(),
        name="certificate_detail",
    ),
    path(
        "certificate/<str:certificate_id>/download/",
        views.CertificateDownloadView.as_view(),
        name="certificate_download",
    ),
    path("verify/", views.VerifyIndexView.as_view(), name="verify_index"),
    path(
        "verify/<str:certificate_id>/",
        views.VerifyCertificateView.as_view(),
        name="verify",
    ),
]
