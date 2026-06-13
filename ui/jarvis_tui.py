"""Jarvis TUI — Modern, minimal terminal interface."""

import asyncio
from typing import Optional

from textual.app import App, ComposeResult
from textual.containers import Vertical, Container
from textual.widgets import RichLog, Input, Static
from textual.reactive import reactive
from textual.widget import Widget
from textual import work


SPINNER_FRAMES = ["◐", "◓", "◑", "◒"]


class StatusLine(Widget):
    status: reactive[str] = reactive("waiting")

    def render(self) -> str:
        icons = {
            "waiting": "○",
            "listening": "◎",
            "processing": "●",
            "speaking": "◉",
            "error": "○",
        }
        labels = {
            "waiting": "AWAITING INPUT",
            "listening": "LISTENING",
            "processing": "PROCESSING",
            "speaking": "SPEAKING",
            "error": "ERROR",
        }
        icon = icons.get(self.status, "○")
        label = labels.get(self.status, self.status.upper())
        return f"  {icon}  {label}"


class Conversation(RichLog):
    def __init__(self):
        super().__init__(highlight=True, markup=True, wrap=True, max_lines=500)
        self.styles.background = "#0a0e1a"
        self.styles.color = "#c8d6ff"

    def system(self, msg: str):
        self.write(f"[#4a9eff]{msg}[/]")

    def you(self, msg: str):
        self.write(f"\n[#7ecb8e]╱ {msg}[/]")

    def jarvis(self, msg: str):
        self.write(f"[#4a9eff]╲ {msg}[/]")

    def error(self, msg: str):
        self.write(f"\n[#ff4444]╱ {msg}[/]")


class JarvisTUI(App):
    TITLE = "jarvis"
    CSS = """
    Screen {
        background: #0a0e1a;
    }

    Static#title {
        color: #4a9eff;
        text-style: bold;
        padding: 0 2;
        background: #0a0e1a;
        height: 1;
    }

    Static#divider {
        color: #1a2a4a;
        background: #0a0e1a;
        height: 1;
    }

    StatusLine {
        background: #0a0e1a;
        color: #4a9eff;
        text-style: bold;
        height: 1;
        padding: 0 2;
    }

    Input {
        background: #0f1428;
        color: #c8d6ff;
        border: none;
        margin: 0 1;
        padding: 0 1;
        height: 2;
    }

    Input:focus {
        background: #141a32;
    }
    """

    def __init__(self, assistant_cls=None, config=None):
        super().__init__()
        self._assistant_cls = assistant_cls
        self._config = config
        self._assistant = None
        self._voice_task: Optional[asyncio.Task] = None
        self._orch = None
        self._spin_index = 0
        self._spinner_task: Optional[asyncio.Task] = None
        self._spin_active = False

    def compose(self) -> ComposeResult:
        yield Static("JARVIS", id="title")
        yield Static("─" * 100, id="divider")
        yield Conversation()
        yield StatusLine()
        yield Input(placeholder="type or say \"Jarvis\"...")

    def on_mount(self) -> None:
        self.query_one(Conversation).system("ready.")
        self.query_one(Input).focus()
        if self._config:
            self._voice_task = asyncio.create_task(self._run_assistant())

    async def _run_assistant(self):
        try:
            if not self._config:
                from core.config import load_config
                self._config = load_config()
            if not self._assistant_cls:
                from core.assistant import JarvisAssistant
                self._assistant_cls = JarvisAssistant
            assistant = self._assistant_cls(self._config, tui=self)
            self._assistant = assistant
            await assistant.initialize()
            self.update_status("waiting")
            await assistant.run()
        except Exception as e:
            self.log_error(f"assistant error: {e}")
            self.update_status("error")
        finally:
            if self._assistant:
                await self._assistant.shutdown()

    async def _spin(self):
        self._spin_active = True
        while self._spin_active:
            self._spin_index = (self._spin_index + 1) % len(SPINNER_FRAMES)
            status = self.query_one(StatusLine)
            status.status = self._status_cache if hasattr(self, '_status_cache') else "processing"
            await asyncio.sleep(0.15)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        text = event.value.strip()
        if not text:
            return
        if text.lower() in ("exit", "quit", "q"):
            self.exit()
            return
        self.query_one(Input).clear()
        self.query_one(Conversation).you(text)
        self.update_status("processing")
        asyncio.create_task(self._handle_text_command(text))

    async def _handle_text_command(self, text: str):
        try:
            if self._assistant and self._assistant.orchestrator:
                response = await self._assistant.orchestrator.process(text)
            else:
                if not self._orch:
                    from core.config import load_config
                    from core.orchestrator import Orchestrator
                    self._orch = Orchestrator.from_config(load_config())
                response = await self._orch.process(text)
            if response:
                self.query_one(Conversation).jarvis(response)
                if self._assistant and self._assistant._tts:
                    self.update_status("speaking")
                    await self._assistant._tts.speak(response)
            self.update_status("waiting")
        except Exception as e:
            self.query_one(Conversation).error(str(e))
            self.update_status("waiting")

    # --- Public API for assistant ---

    def update_status(self, status: str):
        try:
            self._status_cache = status
            self.query_one(StatusLine).status = status
        except Exception:
            pass

    def add_you(self, text: str):
        try:
            self.query_one(Conversation).you(text)
        except Exception:
            pass

    def add_jarvis(self, text: str):
        try:
            self.query_one(Conversation).jarvis(text)
        except Exception:
            pass

    def add_error(self, text: str):
        try:
            self.query_one(Conversation).error(text)
        except Exception:
            pass

    def on_unmount(self) -> None:
        if self._voice_task and not self._voice_task.done():
            self._voice_task.cancel()
