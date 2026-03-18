from django.core.management.base import BaseCommand

from lms.models import Course, Module, Lesson


class Command(BaseCommand):
    help = "Create the Prompt Engineering course with default modules and lessons."

    def handle(self, *args, **options):
        title = "Prompt Engineering"

        course, created = Course.objects.get_or_create(
            slug="prompt-engineering",
            defaults={
                "title": title,
                "description": (
                    "A practical, hands-on course that teaches you how to design, "
                    "test, and refine prompts for real-world AI productivity."
                ),
                "price": 2499,
                "is_published": True,
            },
        )

        if created:
            self.stdout.write(self.style.SUCCESS(f"Created course: {course.title}"))
        else:
            self.stdout.write(self.style.WARNING(f"Course already exists: {course.title}"))

        # Basic 7-day structure (one module per day)
        module_specs = [
            (1, "Foundations of Prompt Engineering"),
            (2, "Prompt Structures & Advanced Techniques"),
            (3, "Role-based Prompts for Work"),
            (4, "Productivity Workflows & Automation"),
            (5, "Domain-specific Prompting"),
            (6, "Portfolio-ready Prompt Projects"),
            (7, "Final Exam & CPEP Prep"),
        ]

        for order, (day, module_title) in enumerate(module_specs, start=1):
            module, m_created = Module.objects.get_or_create(
                course=course,
                release_day=day,
                defaults={
                    "title": module_title,
                    "order": order,
                },
            )
            if m_created:
                self.stdout.write(self.style.SUCCESS(f"  Created module: Day {day} – {module_title}"))
            else:
                self.stdout.write(self.style.WARNING(f"  Module already exists: Day {day} – {module_title}"))

            # Create a single demo lesson per day if none exist
            if not module.lessons.exists():
                lesson = Lesson.objects.create(
                    module=module,
                    title=f"Day {day} – Core Lesson",
                    video_key="",  # Uses demo S3 video key from settings in LessonView
                    order=1,
                    duration_seconds=600,
                )
                self.stdout.write(self.style.SUCCESS(f"    Created lesson: {lesson.title}"))
            else:
                self.stdout.write(self.style.WARNING(f"    Lessons already exist for Day {day}, skipping."))

        self.stdout.write(self.style.SUCCESS("Prompt Engineering course setup complete."))

