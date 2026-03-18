from django.core.management.base import BaseCommand, CommandError

from lms.models import DayQuizQuestion, Module


class Command(BaseCommand):
    help = (
        "Create a 10-question day quiz template for a module.\n"
        "Usage: python manage.py create_day_quizzes --module-id=<id> "
        "or python manage.py create_day_quizzes --course-slug=<slug> --day=<release_day>"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--module-id",
            type=int,
            help="ID of the Module (day) to attach questions to.",
        )
        parser.add_argument(
            "--course-slug",
            type=str,
            help="Course slug to locate the Module (used with --day).",
        )
        parser.add_argument(
            "--day",
            type=int,
            help="Release day number for the Module (used with --course-slug).",
        )

    def handle(self, *args, **options):
        module_id = options.get("module_id")
        course_slug = options.get("course_slug")
        day = options.get("day")

        module = None

        if module_id:
            try:
                module = Module.objects.get(pk=module_id)
            except Module.DoesNotExist:
                raise CommandError(f"Module with id={module_id} does not exist.")
        elif course_slug and day:
            try:
                module = Module.objects.select_related("course").get(
                    course__slug=course_slug,
                    release_day=day,
                )
            except Module.DoesNotExist:
                raise CommandError(
                    f"No module found for course slug '{course_slug}' and day '{day}'."
                )
        else:
            raise CommandError(
                "You must provide either --module-id or both --course-slug and --day."
            )

        self.stdout.write(
            self.style.NOTICE(
                f"Creating quiz questions for module: "
                f"{module.course.title} – Day {module.release_day}: {module.title}"
            )
        )

        if module.day_quiz_questions.exists():
            self.stdout.write(
                self.style.WARNING(
                    "This module already has quiz questions. "
                    "New placeholders will be appended after existing ones."
                )
            )

        # Start order after any existing questions
        start_order = (
            module.day_quiz_questions.order_by("-order", "-id")
            .values_list("order", flat=True)
            .first()
            or 0
        )

        created_count = 0
        for i in range(1, 11):
            order = start_order + i
            q = DayQuizQuestion.objects.create(
                module=module,
                text=f"Placeholder question {order} for Day {module.release_day}. "
                f"Edit this text in the admin.",
                option_1="Option A",
                option_2="Option B",
                option_3="Option C",
                option_4="Option D",
                correct_option=1,
                order=order,
            )
            created_count += 1
            self.stdout.write(self.style.SUCCESS(f"  Created Q{order}: id={q.pk}"))

        self.stdout.write(
            self.style.SUCCESS(
                f"Created {created_count} quiz questions for module id={module.id}."
            )
        )

