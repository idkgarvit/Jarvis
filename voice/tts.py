import asyncio
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class EdgeTTS:
    def __init__(self, voice: str = "en-US-GuyNeural", speed: float = 1.0):
        self.voice = voice
        self.speed = speed
        self._available = False

    def initialize(self):
        try:
            import edge_tts
            self._available = True
            logger.info(f"Edge-TTS initialized with voice: {self.voice}")
        except ImportError:
            logger.warning("edge-tts not installed, TTS unavailable")
            self._available = False

    async def speak(self, text: str):
        if not self._available:
            logger.warning("TTS not available, printing instead")
            print(f"[JARVIS]: {text}")
            return

        import edge_tts
        communicate = edge_tts.Communicate(text, self.voice, rate=f"+{int((self.speed - 1.0) * 100)}%")
        await communicate.save("data/response.mp3")

        import sounddevice as sd
        import soundfile as sf
        data, sr = sf.read("data/response.mp3")
        sd.play(data, sr)
        sd.wait()

    def shutdown(self):
        pass


class PiperTTS:
    def __init__(self, model_dir: str = "", voice: str = "en_US-lessac-medium", speed: float = 1.0):
        self.model_dir = model_dir
        self.voice = voice
        self.speed = speed
        self._available = False

    def initialize(self):
        try:
            import piper
            model_path = f"{self.model_dir}/{self.voice}.onnx"
            self._piper = piper.PiperVoice(model_path)
            self._available = True
            logger.info(f"Piper TTS initialized with voice: {self.voice}")
        except Exception as e:
            logger.warning(f"Piper TTS unavailable ({e})")
            self._available = False

    def speak(self, text: str):
        if not self._available:
            logger.warning("Piper TTS not available")
            return

        import sounddevice as sd
        audio = self._piper.synthesize(text)
        sd.play(audio, self._piper.sample_rate)
        sd.wait()

    def shutdown(self):
        self._piper = None


def create_tts_engine(config):
    engine = getattr(config, "engine", "edge-tts")
    if engine == "piper":
        return PiperTTS(
            model_dir=getattr(config, "piper_model_dir", ""),
            voice=getattr(config, "voice", "en_US-lessac-medium"),
            speed=getattr(config, "speed", 1.0),
        )
    return EdgeTTS(
        voice=getattr(config, "voice", "en-US-GuyNeural"),
        speed=getattr(config, "speed", 1.0),
    )
