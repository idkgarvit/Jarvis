"""Safety and permissions system for Jarvis."""

import json
import logging
import os
from datetime import datetime
from enum import Enum
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    SAFE = "safe"
    CONFIRM = "confirm"
    DANGEROUS = "dangerous"
    BLOCKED = "blocked"


class ActionLogger:
    def __init__(self, log_dir: str = "~/.local/share/jarvis/logs"):
        self.log_dir = os.path.expanduser(log_dir)
        os.makedirs(self.log_dir, exist_ok=True)

    def log_action(self, action: str, details: dict = None, result: str = "success"):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "details": details or {},
            "result": result,
        }
        log_file = os.path.join(self.log_dir, f"actions_{datetime.now().strftime('%Y-%m')}.jsonl")
        with open(log_file, "a") as f:
            f.write(json.dumps(entry) + "\n")


class SafetyManager:
    SAFE_ACTIONS = {
        "open_app", "read_file", "search_web", "get_weather", "get_time",
        "set_reminder", "take_note", "list_dir", "get_notes", "get_reminders",
        "clipboard_read", "screenshot", "get_system_info", "get_news",
        "git_status", "git_pull", "git_log", "morning_briefing",
        "list_processes", "search_files", "summarize_page",
    }

    CONFIRM_ACTIONS = {
        "delete_file", "kill_process", "run_shell", "lock_screen",
        "write_file", "move_file",
    }

    DANGEROUS_ACTIONS = {
        "format_disk", "rm_rf", "wipe_data",
    }

    def __init__(self, config: dict = None):
        self.logger = ActionLogger()
        if config:
            extra_safe = config.get("safe_actions", [])
            self.SAFE_ACTIONS.update(extra_safe)

    def classify(self, tool_name: str, args: dict = None) -> RiskLevel:
        if tool_name in self.DANGEROUS_ACTIONS:
            return RiskLevel.BLOCKED
        if tool_name in self.CONFIRM_ACTIONS:
            return RiskLevel.CONFIRM
        if tool_name in self.SAFE_ACTIONS:
            return RiskLevel.SAFE
        return RiskLevel.CONFIRM

    def record(self, action: str, details: dict = None, result: str = "success"):
        self.logger.log_action(action, details, result)
