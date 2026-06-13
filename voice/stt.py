import json
import logging
import threading
import numpy as np
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class VoskSTT:
    def __init__(self, model_path: str = "~/.cache/jarvis/vosk-model", language: str = "en"):
        self.model_path = Path(model_path).expanduser()
        self.language = language
        self._model = None
        self._lock = threading.Lock()

    def initialize(self):
        try:
            from vosk import Model, KaldiRecognizer
            if not self.model_path.exists():
                logger.info(f"Downloading Vosk model to {self.model_path}...")
                import urllib.request
                import tarfile
                url = "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip"
                self.model_path.parent.mkdir(parents=True, exist_ok=True)
                zip_path = self.model_path.parent / "vosk-model.zip"
                urllib.request.urlretrieve(url, zip_path)
                import zipfile
                with zipfile.ZipFile(zip_path, 'r') as zf:
                    zf.extractall(self.model_path.parent)
                extracted = list(self.model_path.parent.glob("vosk-model-small-en-us-*"))
                if extracted:
                    extracted[0].rename(self.model_path)
                zip_path.unlink()
            self._model = Model(str(self.model_path))
            logger.info(f"Vosk model loaded: {self.model_path}")
        except Exception as e:
            logger.error(f"Vosk init failed: {e}")
            raise

    def transcribe(self, audio: np.ndarray) -> Optional[str]:
        with self._lock:
            if self._model is None:
                raise RuntimeError("Vosk not initialized")
            from vosk import KaldiRecognizer
            rec = KaldiRecognizer(self._model, 16000)
            audio_int16 = audio.astype(np.int16).tobytes()
            rec.AcceptWaveform(audio_int16)
            result = json.loads(rec.FinalResult())
            text = result.get("text", "").strip()
            return text if text else None

    def shutdown(self):
        self._model = None


class FasterWhisperSTT:
    def __init__(
        self,
        model: str = "base.en",
        device: str = "auto",
        compute_type: str = "int8",
        language: str = "en",
        beam_size: int = 5,
        vad_filter: bool = True,
    ):
        self.model_name = model
        self.device = device
        self.compute_type = compute_type
        self.language = language
        self.beam_size = beam_size
        self.vad_filter = vad_filter
        self._model = None

    def initialize(self):
        try:
            from faster_whisper import WhisperModel
            import torch

            if self.device == "auto":
                self.device = "cuda" if torch.cuda.is_available() else "cpu"

            self._model = WhisperModel(
                self.model_name,
                device=self.device,
                compute_type=self.compute_type,
                num_workers=2,
            )
            logger.info(f"faster-whisper loaded: {self.model_name} on {self.device}")
        except Exception as e:
            logger.error(f"Failed to load faster-whisper: {e}")
            raise

    def transcribe(self, audio: np.ndarray) -> Optional[str]:
        if self._model is None:
            raise RuntimeError("STT not initialized")

        audio_float = audio.astype(np.float32)
        if audio_float.max() > 1.0:
            audio_float = audio_float / 32768.0

        segments, info = self._model.transcribe(
            audio_float,
            language=self.language,
            beam_size=self.beam_size,
            vad_filter=self.vad_filter,
        )

        text = " ".join(seg.text for seg in segments)
        return text.strip() if text.strip() else None

    def shutdown(self):
        self._model = None


def create_stt_engine(config):
    engine = getattr(config, "engine", "faster-whisper")
    if engine == "vosk":
        return VoskSTT(
            model_path=getattr(config, "vosk_model_path", "~/.cache/jarvis/vosk-model"),
            language=getattr(config, "language", "en"),
        )
    return FasterWhisperSTT(
        model=getattr(config, "model", "base.en"),
        device=getattr(config, "device", "auto"),
        compute_type=getattr(config, "compute_type", "int8"),
        language=getattr(config, "language", "en"),
        beam_size=getattr(config, "beam_size", 5),
        vad_filter=getattr(config, "vad_filter", True),
    )
