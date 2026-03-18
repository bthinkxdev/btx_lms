"""
LMS utility functions.
"""
from django.utils.text import slugify


def unique_slug_from_title(model_class, title: str, slug_field: str = "slug", pk=None) -> str:
    """
    Generate a unique slug from title for the given model.
    Optionally exclude pk when updating.
    """
    base = slugify(title) or "item"
    slug = base
    num = 0
    qs = model_class.objects.all()
    if pk is not None:
        qs = qs.exclude(pk=pk)
    while qs.filter(**{slug_field: slug}).exists():
        num += 1
        slug = f"{base}-{num}"
    return slug
