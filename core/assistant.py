import asyncio
import logging
import signal
import sys
from typing import Optional
from pathlib import Path

from .config import Config, load_config
from .events import EventBus, Event, Events, get_event_bus
from .plugin import PluginManager
from .orchestrator import Orchestrator
from .memory import MemoryManager

logger = logging.getLogger(__name__)


class JarvisAssistant:
    def __init__(self, config: Config = None, tui=None):
        self.config = config or load_config()
        self.event_bus = get_event_bus()
        self.plugin_manager = PluginManager(self.config, self.event_bus)
        self.orchestrator = None
        self.tui = tui

        self._stt = None
        self._tts = None
        self._wake_word = None
        self._browser = None
        self._memory = None
        self._integrations = {}

        self._running = False
        self._ui = None

    async def initialize(self):
        logger.info("Initializing Jarvis...")
        self._create_directories()
        await self.plugin_manager.load_plugins()

        self._tts = await self._init_tts()
        self._stt = await self._init_stt()
        self._wake_word = await self._init_wake_word()
        self._memory = self._init_memory()

        self.orchestrator = Orchestrator.from_config(self.config)
        self._subscribe_events()

        logger.info("Jarvis initialized successfully")
        await self.event_bus.emit_async(Event(
            type=Events.STARTUP,
            data={"version": self.config.general.version},
            source="assistant",
        ))

    def _create_directories(self):
        dirs = [
            self.config.general.data_dir,
            self.config.general.config_dir,
            self.config.general.cache_dir,
        ]
        for dir_path in dirs:
            Path(dir_path).mkdir(parents=True, exist_ok=True)

    async def _init_stt(self):
        try:
            from voice.stt import create_stt_engine
            engine = create_stt_engine(self.config.stt)
            engine.initialize()
            return engine
        except Exception as e:
            logger.warning(f"STT init failed: {e}")
            return None

    async def _init_tts(self):
        try:
            from voice.tts import EdgeTTS
            engine = EdgeTTS(
                voice=self.config.tts.voice,
                speed=self.config.tts.speed,
            )
            engine.initialize()
            return engine
        except Exception as e:
            logger.warning(f"TTS init failed: {e}")
            return None

    async def _init_wake_word(self):
        if not self.config.wake_word.enabled:
            return None
        try:
            from voice.wake_word import PorcupineWakeWord
            engine = PorcupineWakeWord(
                keywords=self.config.wake_word.keywords,
                sensitivity=self.config.wake_word.sensitivity,
            )
            engine.initialize()
            return engine
        except Exception as e:
            logger.warning(f"Wake word init failed: {e}")
            return None

    def _init_memory(self):
        try:
            return MemoryManager(
                db_path=f"{self.config.general.data_dir}/memory.db",
            )
        except Exception as e:
            logger.warning(f"Memory init failed: {e}")
            return None

    def _subscribe_events(self):
        self.event_bus.subscribe(Events.WAKE_WORD_DETECTED, self._on_wake_word)
        self.event_bus.subscribe(Events.SPEECH_RECOGNIZED, self._on_speech_recognized)
        self.event_bus.subscribe(Events.COMMAND_RECEIVED, self._on_command)

    async def _on_wake_word(self, event: Event):
        logger.info("Wake word detected")
        if self.tui:
            self.tui.update_status("LISTENING")
        text = event.data.get("text", "") if event.data else ""
        if self._tts and not text:
            await self._tts.speak("Yes, sir?")
        if self._stt:
            try:
                if text:
                    if self.tui:
                        self.tui.add_you(text)
                    await self._on_command(Event(
                        type=Events.COMMAND_RECEIVED,
                        data={"text": text, "source": "voice"},
                        source="assistant",
                    ))
                    return
                from voice.audio import AudioCapture
                audio = AudioCapture()
                audio.start()
                audio_data = audio.read_silence_detected()
                audio.stop()
                text = self._stt.transcribe(audio_data)
                if text:
                    if self.tui:
                        self.tui.add_you(text)
                    await self.event_bus.emit_async(Event(
                        type=Events.COMMAND_RECEIVED,
                        data={"text": text, "source": "voice"},
                        source="stt",
                    ))
            except Exception as e:
                logger.error(f"STT capture failed: {e}")

    async def _on_speech_recognized(self, event: Event):
        text = event.data.get("text", "")
        if text:
            await self.event_bus.emit_async(Event(
                type=Events.COMMAND_RECEIVED,
                data={"text": text, "source": "voice"},
                source="stt",
            ))

    async def _on_command(self, event: Event):
        text = event.data.get("text", "")
        source = event.data.get("source", "unknown")

        logger.info(f"Processing: {text} (from {source})")
        if self.tui:
            self.tui.update_status("PROCESSING")

        await self.event_bus.emit_async(Event(
            type=Events.COMMAND_PROCESSING,
            data={"text": text},
            source="assistant",
        ))

        try:
            response = await self.plugin_manager.handle_command(text, {"source": source})
            if response is None and self.orchestrator:
                response = await self.orchestrator.process(text)

            if response:
                if self.tui:
                    self.tui.add_jarvis(response)
                if self._tts:
                    if self.tui:
                        self.tui.update_status("SPEAKING")
                    await self._tts.speak(response)
                else:
                    logger.info(f"Response: {response}")

            if self.tui:
                self.tui.update_status("WAITING")

            await self.event_bus.emit_async(Event(
                type=Events.COMMAND_COMPLETED,
                data={"text": text, "response": response},
                source="assistant",
            ))
        except Exception as e:
            logger.error(f"Command error: {e}")
            if self.tui:
                self.tui.update_status("WAITING")
            await self.event_bus.emit_async(Event(
                type=Events.COMMAND_FAILED,
                data={"text": text, "error": str(e)},
                source="assistant",
            ))

    async def run(self):
        self._running = True
        self._loop = asyncio.get_running_loop()
        if self.tui:
            self.tui.update_status("WAITING")

        if self._wake_word:
            self._wake_word.start(
                callback=lambda text="": asyncio.run_coroutine_threadsafe(
                    self._on_wake_word(Event(
                        type=Events.WAKE_WORD_DETECTED,
                        data={"text": text} if text else {},
                        source="wake_word",
                    )),
                    self._loop,
                ),
                stt_engine=self._stt,
            )

        try:
            while self._running:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            pass

    async def shutdown(self):
        logger.info("Shutting down Jarvis...")
        self._running = False
        if self._wake_word:
            self._wake_word.stop()
        if self.orchestrator:
            self.orchestrator.shutdown()
        await self.plugin_manager.shutdown_all()
        await self.event_bus.emit_async(Event(
            type=Events.SHUTDOWN,
            source="assistant",
        ))
        logger.info("Jarvis shutdown complete")
