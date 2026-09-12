"""Small invoice-reminder fixture with an intentional null due-date bug."""

from __future__ import annotations

from datetime import date


def format_due_date(due_date: date | None) -> str:
    """Return the due date text used by the reminder template."""

    return due_date.strftime("%d %B %Y")
