"""
Custom template filters for LMS.
"""
import re
from django import template

register = template.Library()


@register.filter
def get_item(d, key):
    """Return d[key]; use in template as dict|get_item:key."""
    if d is None:
        return None
    try:
        return d.get(key)
    except (AttributeError, TypeError):
        return None


@register.filter
def course_day_sections(description):
    """
    Split course description into day sections for collapsible curriculum.
    Returns list of {day: int, title: str, content: str}.
    Intro (before DAY 1) has day=0.
    """
    if not description or not isinstance(description, str):
        return []
    sections = []
    # Split by "DAY N – " or "DAY N - " (en-dash or hyphen)
    pattern = re.compile(r'\n(?=DAY \d+ [–\-] )', re.IGNORECASE)
    parts = pattern.split(description.strip())
    intro = parts[0].strip() if parts else ""
    if intro:
        sections.append({"day": 0, "title": "Overview", "content": intro})
    for part in parts[1:]:
        part = part.strip()
        if not part:
            continue
        m = re.match(r'DAY (\d+) [–\-] (.+?)(?:\n|$)', part, re.DOTALL | re.IGNORECASE)
        if m:
            day_num = int(m.group(1))
            title = m.group(2).strip()
            content = part[m.end():].strip()
            sections.append({"day": day_num, "title": title, "content": content})
    return sections
