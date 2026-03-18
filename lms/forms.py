"""
LMS forms for enrollment, registration, and validation.
"""
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError

from lms.models import Enrollment, Exam, ExamResult, UserProfile

User = get_user_model()


class UserProfileForm(forms.ModelForm):
    """Learner profile, partial saves OK; completion recalculated on save."""

    class Meta:
        model = UserProfile
        fields = (
            "full_name",
            "phone",
            "location",
            "profile_photo",
            "bio",
            "highest_education",
            "college",
            "graduation_year",
            "experience",
            "skills",
            "linkedin_url",
            "portfolio_url",
            "is_public",
            "public_whatsapp_contact",
            "public_email_contact",
            "available_for_freelance",
        )
        widgets = {
            "full_name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Your full name"}
            ),
            "phone": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "e.g. WhatsApp number"}
            ),
            "location": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "City, Country"}
            ),
            "bio": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Short intro, who you are and what you're learning",
                }
            ),
            "highest_education": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "e.g. Bachelor's, Master's"}
            ),
            "college": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "School or university"}
            ),
            "graduation_year": forms.NumberInput(
                attrs={"class": "form-control", "placeholder": "Year", "min": 1950, "max": 2035}
            ),
            "experience": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 5,
                    "placeholder": "Roles, projects, or freelance work (plain text)",
                }
            ),
            "skills": forms.HiddenInput(attrs={"id": "id_skills"}),
            "linkedin_url": forms.URLInput(
                attrs={
                    "class": "form-control profile-input-full",
                    "placeholder": "https://www.linkedin.com/in/your-profile",
                    "autocomplete": "url",
                }
            ),
            "portfolio_url": forms.URLInput(
                attrs={
                    "class": "form-control profile-input-full",
                    "placeholder": "https://yourportfolio.com",
                    "autocomplete": "url",
                }
            ),
            "profile_photo": forms.FileInput(
                attrs={
                    "class": "profile-photo-native-input",
                    "accept": "image/jpeg,image/png,image/webp,image/gif",
                    "id": "id_profile_photo",
                }
            ),
            "is_public": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "public_whatsapp_contact": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
            "public_email_contact": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
            "available_for_freelance": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
        }
        labels = {
            "is_public": "Public portfolio page",
            "public_whatsapp_contact": "Show WhatsApp contact on public page",
            "public_email_contact": "Show email contact on public page",
            "available_for_freelance": "Show “Available for freelance” badge",
        }
        help_texts = {
            "is_public": "When off, /u/your-username/ shows 404.",
            "public_whatsapp_contact": "Uses the phone number above. Only enable if you’re comfortable sharing it.",
            "public_email_contact": "Uses your login email. Only enable if you want hiring contacts via email.",
        }


class ProfileBasicSectionForm(forms.ModelForm):
    """Dashboard modal: photo, name, phone, location."""

    class Meta:
        model = UserProfile
        fields = ("full_name", "phone", "location", "profile_photo")
        widgets = {
            "full_name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Your full name"}
            ),
            "phone": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "e.g. WhatsApp number"}
            ),
            "location": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "City, Country"}
            ),
            "profile_photo": forms.FileInput(
                attrs={
                    "class": "profile-photo-native-input",
                    "accept": "image/jpeg,image/png,image/webp,image/gif",
                }
            ),
        }


class ProfileBioSectionForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ("bio",)
        widgets = {
            "bio": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Short intro, who you are and what you're learning",
                }
            ),
        }


class ProfileEducationSectionForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ("highest_education", "college", "graduation_year")
        widgets = {
            "highest_education": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "e.g. Bachelor's, Master's"}
            ),
            "college": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "School or university"}
            ),
            "graduation_year": forms.NumberInput(
                attrs={"class": "form-control", "placeholder": "Year", "min": 1950, "max": 2035}
            ),
        }


class ProfileExperienceSectionForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ("experience",)
        widgets = {
            "experience": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 6,
                    "placeholder": "Roles, projects, or freelance work (plain text)",
                }
            ),
        }


class ProfileSkillsSectionForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ("skills",)
        widgets = {"skills": forms.HiddenInput()}


class ProfilePortfolioSectionForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = (
            "is_public",
            "public_whatsapp_contact",
            "public_email_contact",
            "available_for_freelance",
            "linkedin_url",
            "portfolio_url",
        )
        widgets = {
            "linkedin_url": forms.URLInput(
                attrs={
                    "class": "form-control profile-input-full",
                    "placeholder": "https://www.linkedin.com/in/your-profile",
                    "autocomplete": "url",
                }
            ),
            "portfolio_url": forms.URLInput(
                attrs={
                    "class": "form-control profile-input-full",
                    "placeholder": "https://yourportfolio.com",
                    "autocomplete": "url",
                }
            ),
            "is_public": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "public_whatsapp_contact": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
            "public_email_contact": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
            "available_for_freelance": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
        }
        labels = UserProfileForm.Meta.labels
        help_texts = UserProfileForm.Meta.help_texts


class EnrollForm(forms.Form):
    """Mock enrollment form (confirm to create enrollment after payment)."""
    confirm = forms.BooleanField(
        required=True,
        label="I confirm my enrollment",
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )

    def __init__(self, *args, user=None, course=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._user = user
        self._course = course

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get("confirm"):
            return cleaned
        if self._user is None or not self._user.is_authenticated:
            raise ValidationError("You must be logged in to enroll.")
        if self._course is None:
            raise ValidationError("Invalid course.")
        if Enrollment.objects.filter(user=self._user, course=self._course).exists():
            raise ValidationError("You are already enrolled in this course.")
        return cleaned


class ExamResultForm(forms.ModelForm):
    """Form for uploading exam result (score); pass/fail computed in model save."""

    class Meta:
        model = ExamResult
        fields = ("exam", "user", "score", "notes")
        widgets = {
            "exam": forms.Select(attrs={"class": "form-select"}),
            "user": forms.Select(attrs={"class": "form-select"}),
            "score": forms.NumberInput(attrs={"class": "form-control", "min": 0, "max": 100}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
        }

    def clean_score(self):
        value = self.cleaned_data.get("score")
        if value is not None and (value < 0 or value > 100):
            raise ValidationError("Score must be between 0 and 100.")
        return value


class RegisterForm(UserCreationForm):
    """User registration form."""

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")
        widgets = {
            "username": forms.TextInput(attrs={"class": "form-control", "autofocus": True}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in ("password1", "password2"):
            if field in self.fields:
                self.fields[field].widget.attrs["class"] = "form-control"
