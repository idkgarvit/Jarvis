"""
Event System for Jarvis
=======================
Pub/sub event bus for loose coupling between components.
"""

import asyncio
import logging
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid

logger = logging.getLogger(__name__)


class EventPriority(Enum):
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


@dataclass
class Event:
    """Event data structure."""
    type: str
    data: Any = None
    source: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    priority: EventPriority = EventPriority.NORMAL
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __lt__(self, other):
        return self.priority.value > other.priority.value


class EventBus:
    """
    Async event bus for inter-component communication.
    Supports priority-based event handling and async/sync handlers.
    """

    def __init__(self):
        self._handlers: Dict[str, List[Callable]] = {}
        self._async_handlers: Dict[str, List[Callable]] = {}
        self._wildcard_handlers: List[Callable] = []
        self._async_wildcard_handlers: List[Callable] = []
        self._event_history: List[Event] = []
        self._max_history = 1000
        self._running = False

    def subscribe(self, event_type: str, handler: Callable, async_handler: bool = False):
        """Subscribe to an event type."""
        if async_handler:
            if event_type not in self._async_handlers:
                self._async_handlers[event_type] = []
            self._async_handlers[event_type].append(handler)
        else:
            if event_type not in self._handlers:
                self._handlers[event_type] = []
            self._handlers[event_type].append(handler)
        logger.debug(f"Subscribed {'async' if async_handler else 'sync'} handler to {event_type}")

    def subscribe_all(self, handler: Callable, async_handler: bool = False):
        """Subscribe to all events (wildcard)."""
        if async_handler:
            self._async_wildcard_handlers.append(handler)
        else:
            self._wildcard_handlers.append(handler)

    def unsubscribe(self, event_type: str, handler: Callable):
        """Unsubscribe from an event type."""
        if event_type in self._handlers:
            self._handlers[event_type].remove(handler)
        if event_type in self._async_handlers:
            self._async_handlers[event_type].remove(handler)

    def emit(self, event: Event):
        """Emit an event synchronously."""
        self._event_history.append(event)
        if len(self._event_history) > self._max_history:
            self._event_history.pop(0)

        # Call wildcard handlers first
        for handler in self._wildcard_handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Wildcard handler error: {e}")

        # Call specific handlers
        handlers = self._handlers.get(event.type, [])
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Handler error for {event.type}: {e}")

    async def emit_async(self, event: Event):
        """Emit an event asynchronously."""
        self._event_history.append(event)
        if len(self._event_history) > self._max_history:
            self._event_history.pop(0)

        # Call wildcard handlers
        tasks = []
        for handler in self._async_wildcard_handlers:
            tasks.append(self._safe_async_call(handler, event))
        for handler in self._wildcard_handlers:
            tasks.append(self._safe_sync_call(handler, event))

        # Call specific handlers
        async_handlers = self._async_handlers.get(event.type, [])
        sync_handlers = self._handlers.get(event.type, [])

        for handler in async_handlers:
            tasks.append(self._safe_async_call(handler, event))
        for handler in sync_handlers:
            tasks.append(self._safe_sync_call(handler, event))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _safe_async_call(self, handler: Callable, event: Event):
        try:
            await handler(event)
        except Exception as e:
            logger.error(f"Async handler error for {event.type}: {e}")

    async def _safe_sync_call(self, handler: Callable, event: Event):
        try:
            handler(event)
        except Exception as e:
            logger.error(f"Sync handler error for {event.type}: {e}")

    def get_history(self, event_type: Optional[str] = None, limit: int = 100) -> List[Event]:
        """Get event history, optionally filtered by type."""
        events = self._event_history
        if event_type:
            events = [e for e in events if e.type == event_type]
        return events[-limit:]

    def clear_history(self):
        """Clear event history."""
        self._event_history.clear()


# Global event bus instance
_event_bus: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    """Get the global event bus instance."""
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus


# Common event types
class Events:
    # System events
    STARTUP = "system.startup"
    SHUTDOWN = "system.shutdown"
    ERROR = "system.error"

    # Wake word events
    WAKE_WORD_DETECTED = "wake_word.detected"
    WAKE_WORD_TIMEOUT = "wake_word.timeout"

    # Speech events
    SPEECH_STARTED = "speech.started"
    SPEECH_RECOGNIZED = "speech.recognized"
    SPEECH_ERROR = "speech.error"

    # Command events
    COMMAND_RECEIVED = "command.received"
    COMMAND_PROCESSING = "command.processing"
    COMMAND_COMPLETED = "command.completed"
    COMMAND_FAILED = "command.failed"

    # LLM events
    LLM_REQUEST = "llm.request"
    LLM_RESPONSE = "llm.response"
    LLM_STREAMING = "llm.streaming"
    LLM_ERROR = "llm.error"

    # TTS events
    TTS_STARTED = "tts.started"
    TTS_COMPLETED = "tts.completed"
    TTS_ERROR = "tts.error"

    # Browser events
    BROWSER_NAVIGATE = "browser.navigate"
    BROWSER_ACTION = "browser.action"
    BROWSER_RESULT = "browser.result"
    BROWSER_ERROR = "browser.error"

    # Integration events
    GMAIL_NEW_EMAIL = "gmail.new_email"
    GMAIL_SENT = "gmail.sent"
    WHATSAPP_MESSAGE = "whatsapp.message"
    WHATSAPP_RECEIVED = "whatsapp.received"

    # Plugin events
    PLUGIN_LOADED = "plugin.loaded"
    PLUGIN_UNLOADED = "plugin.unloaded"
    PLUGIN_ERROR = "plugin.error"

    # Reminder events
    REMINDER_DUE = "reminder.due"
    REMINDER_CREATED = "reminder.created"

    # Memory events
    MEMORY_STORED = "memory.stored"
    MEMORY_RETRIEVED = "memory.retrieved"