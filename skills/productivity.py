"""Productivity skills: reminders, notes, todos, morning briefing."""

import json
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


_memory = None


def _get_memory():
    global _memory
    if _memory is None:
        from core.memory import MemoryManager
        _memory = MemoryManager()
    return _memory


def take_note(content: str, title: str = "") -> str:
    mem = _get_memory()
    mem.add_note(content, title=title)
    return f"Note saved{' as ' + title if title else ''}"


def get_notes(limit: int = 10) -> str:
    mem = _get_memory()
    notes = mem.get_recent_notes(limit)
    if not notes:
        return "No notes found."
    lines = []
    for n in notes:
        lines.append(f"[{n['created_at'][:16]}] {n['title']}: {n['content'][:100]}")
    return "Recent notes:\n" + "\n".join(lines)


def set_reminder(content: str, due_at: str = "") -> str:
    mem = _get_memory()
    mem.add_reminder(content, due_at)
    return f"Reminder set: {content}" + (f" (due: {due_at})" if due_at else "")


def get_reminders() -> str:
    mem = _get_memory()
    reminders = mem.get_pending_reminders()
    if not reminders:
        return "No pending reminders."
    lines = []
    for r in reminders:
        due = f" (due: {r['due_at']})" if r['due_at'] else ""
        lines.append(f"  • {r['content']}{due}")
    return "Pending reminders:\n" + "\n".join(lines)


def done_reminder(reminder_id: int) -> str:
    mem = _get_memory()
    mem.mark_reminder_done(reminder_id)
    return f"Reminder {reminder_id} marked done"


def morning_briefing() -> str:
    from datetime import date
    import skills.web_info as web

    parts = [f"Good morning. Here's your briefing for {date.today().strftime('%A, %B %d')}."]

    weather = web.get_weather()
    parts.append(f"\nWeather: {weather}")

    news = web.get_news()
    parts.append(f"\nTop news:\n{news}")

    reminders = get_reminders()
    if "No pending" not in reminders:
        parts.append(f"\nReminders:\n{reminders}")

    return "\n".join(parts)
