import logging
import numpy as np
import threading
from typing import Optional, Callable

from .audio import AudioCapture

logger = logging.getLogger(__name__)


class PorcupineWakeWord:
    def __init__(self, keywords: list = None, sensitivity: float = 0.7, access_key: str = ""):
        self.keywords = keywords or ["jarvis", "hey jarvis"]
        self.sensitivity = sensitivity
        self.access_key = access_key
        self._porcupine = None
        self._audio = None
        self._callback: Optional[Callable] = None

    def initialize(self):
        try:
            import pvporcupine
            kwargs = {
                "keywords": self.keywords,
                "sensitivities": [self.sensitivity] * len(self.keywords),
            }
            if self.access_key:
                kwargs["access_key"] = self.access_key
            self._porcupine = pvporcupine.create(**kwargs)
            logger.info(f"Porcupine initialized with keywords: {self.keywords}")
        except Exception as e:
            logger.warning(f"Porcupine init failed ({e}), using keyword-spotting fallback")
            self._porcupine = None

    def start(self, callback: Callable, stt_engine=None):
        self._callback = callback
        if self._porcupine is None:
            logger.warning("Porcupine not available — using KeywordSpotter fallback")
            fallback = KeywordSpotter(self.keywords, stt_engine=stt_engine)
            fallback.start(callback)
            self._fallback = fallback
            return

        self._audio = AudioCapture(sample_rate=self._porcupine.sample_rate)

        def on_audio(frame: np.ndarray):
            if self._porcupine is None:
                return
            audio_flat = (frame * 32767).astype(np.int16).flatten()
            result = self._porcupine.process(audio_flat.tolist())
            if result >= 0:
                logger.info(f"Wake word detected (keyword index: {result})")
                if self._callback:
                    self._callback()

        self._audio.start(callback=on_audio)

    def stop(self):
        if hasattr(self, '_fallback') and self._fallback:
            self._fallback.stop()
            self._fallback = None
        if self._audio:
            self._audio.stop()
        if self._porcupine:
            self._porcupine.delete()
            self._porcupine = None

    @property
    def is_available(self) -> bool:
        return self._porcupine is not None

    @property
    def sample_rate(self) -> int:
        return self._porcupine.sample_rate if self._porcupine else 16000


class KeywordSpotter:
    def __init__(self, keywords: list = None, stt_engine=None):
        self.keywords = [k.lower() for k in (keywords or ["jarvis", "hey jarvis"])]
        self._callback = None
        self._running = False
        self._thread = None

    def start(self, callback: Callable):
        self._callback = callback
        self._running = True
        self._thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._thread.start()
        logger.info("KeywordSpotter started")

    def _listen_loop(self):
        import time
        import sounddevice as sd
        import speech_recognition as sr
        import numpy as np

        r = sr.Recognizer()
        fs = 16000
        chunk_s = 4
        logger.info("Listening (4s chunks via Google API)...")

        while self._running:
            try:
                recording = sd.rec(int(chunk_s * fs), samplerate=fs, channels=1, dtype="int16")
                sd.wait()
                audio = sr.AudioData(recording.tobytes(), fs, 2)
                try:
                    text = r.recognize_google(audio).lower().strip()
                except sr.UnknownValueError:
                    continue
                except sr.RequestError as e:
                    logger.warning(f"Google API error: {e}")
                    time.sleep(2)
                    continue

                logger.info(f"Heard: \"{text}\"")
                for kw in self.keywords:
                    if text.startswith(kw) or f" {kw}" in text:
                        command = self.strip_wake_word(text)
                        logger.info(f"Wake word! Command: \"{command}\"")
                        if self._callback and command:
                            self._callback(command)
                        break
            except Exception as e:
                logger.error(f"Loop error: {e}")
                time.sleep(1)

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=3)

    def stop(self):
        self._running = False
        if self._audio:
            self._audio.stop()
        if self._thread:
            self._thread.join(timeout=2)

    def contains_wake_word(self, text: str) -> bool:
        text_lower = text.lower().strip()
        for kw in self.keywords:
            if text_lower.startswith(kw) or f" {kw}" in text_lower:
                return True
        return False

    def strip_wake_word(self, text: str) -> str:
        text_lower = text.lower().strip()
        for kw in sorted(self.keywords, key=len, reverse=True):
            if text_lower.startswith(kw):
                return text[len(kw):].strip()
            if text_lower.startswith(f"hey {kw}"):
                return text[len(f"hey {kw}"):].strip()
        return text.strip()


def create_wake_word_engine(config) -> PorcupineWakeWord:
    access_key = config.get("access_key", "")
    return PorcupineWakeWord(
        keywords=config.get("keywords", ["jarvis"]),
        sensitivity=config.get("sensitivity", 0.7),
        access_key=access_key,
    )
