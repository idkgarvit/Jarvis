import json
import logging
import os
import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    session_id TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS facts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT UNIQUE NOT NULL,
    value TEXT NOT NULL,
    timestamp TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS reminders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content TEXT NOT NULL,
    due_at TEXT,
    created_at TEXT NOT NULL,
    done INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL,
    tags TEXT DEFAULT ''
);
"""


class MemoryManager:
    def __init__(self, db_path: str = "~/.local/share/jarvis/memory.db"):
        self.db_path = os.path.expanduser(db_path)
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.executescript(SCHEMA_SQL)
        self._conn.commit()
        logger.info(f"Memory DB: {self.db_path}")

    # --- Conversations ---

    def store_conversation(self, role: str, content: str, session_id: str = ""):
        with self._lock:
            self._conn.execute(
                "INSERT INTO conversations (timestamp, role, content, session_id) VALUES (?, ?, ?, ?)",
                (datetime.now().isoformat(), role, content, session_id or "default"),
            )
            self._conn.commit()

    def get_recent_conversations(self, limit: int = 20, session_id: str = "") -> List[Dict]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT timestamp, role, content FROM conversations WHERE session_id = ? ORDER BY id DESC LIMIT ?",
                (session_id or "default", limit),
            ).fetchall()
        return [{"timestamp": r[0], "role": r[1], "content": r[2]} for r in reversed(rows)]

    # --- Facts ---

    def store_fact(self, key: str, value: str):
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO facts (key, value, timestamp) VALUES (?, ?, ?)",
                (key, value, datetime.now().isoformat()),
            )
            self._conn.commit()

    def get_fact(self, key: str) -> Optional[str]:
        with self._lock:
            row = self._conn.execute("SELECT value FROM facts WHERE key = ?", (key,)).fetchone()
        return row[0] if row else None

    def get_all_facts(self) -> Dict[str, str]:
        with self._lock:
            return dict(self._conn.execute("SELECT key, value FROM facts").fetchall())

    def search_facts(self, query: str) -> List[str]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT key, value FROM facts WHERE key LIKE ? OR value LIKE ?",
                (f"%{query}%", f"%{query}%"),
            ).fetchall()
        return [f"{r[0]}: {r[1]}" for r in rows]

    # --- Reminders ---

    def add_reminder(self, content: str, due_at: str = ""):
        with self._lock:
            self._conn.execute(
                "INSERT INTO reminders (content, due_at, created_at) VALUES (?, ?, ?)",
                (content, due_at, datetime.now().isoformat()),
            )
            self._conn.commit()

    def get_pending_reminders(self) -> List[Dict]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT id, content, due_at, created_at FROM reminders WHERE done = 0 ORDER BY due_at ASC"
            ).fetchall()
        return [{"id": r[0], "content": r[1], "due_at": r[2], "created_at": r[3]} for r in rows]

    def mark_reminder_done(self, reminder_id: int):
        with self._lock:
            self._conn.execute("UPDATE reminders SET done = 1 WHERE id = ?", (reminder_id,))
            self._conn.commit()

    # --- Notes ---

    def add_note(self, content: str, title: str = "", tags: str = ""):
        with self._lock:
            self._conn.execute(
                "INSERT INTO notes (title, content, created_at, tags) VALUES (?, ?, ?, ?)",
                (title or datetime.now().strftime("Note %Y-%m-%d %H:%M"), content, datetime.now().isoformat(), tags),
            )
            self._conn.commit()

    def get_recent_notes(self, limit: int = 10) -> List[Dict]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT id, title, content, created_at, tags FROM notes ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [{"id": r[0], "title": r[1], "content": r[2], "created_at": r[3], "tags": r[4]} for r in rows]

    # --- Context building ---

    def build_context(self, query: str = "", limit: int = 10) -> str:
        parts = []
        facts = self.get_all_facts()
        if facts:
            parts.append("### Known Facts\n" + "\n".join(f"{k}: {v}" for k, v in facts.items()))

        notes = self.get_recent_notes(5)
        if notes:
            parts.append("### Recent Notes\n" + "\n".join(f"- {n['title']}: {n['content'][:200]}" for n in notes))

        reminders = self.get_pending_reminders()
        if reminders:
            parts.append("### Pending Reminders\n" + "\n".join(f"- {r['content']}{' (due: ' + r['due_at'] + ')' if r['due_at'] else ''}" for r in reminders))

        history = self.get_recent_conversations(limit)
        if history:
            parts.append("### Recent Conversation\n" + "\n".join(f"{h['role']}: {h['content']}" for h in history[-6:]))

        return "\n\n".join(parts)

    def shutdown(self):
        self._conn.close()
