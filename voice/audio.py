import time
import numpy as np
import sounddevice as sd
import threading
import queue
from typing import Optional, Callable

SAMPLE_RATE = 16000
CHANNELS = 1
DTYPE = np.int16
BLOCK_SIZE = 1024


class AudioCapture:
    def __init__(self, sample_rate: int = SAMPLE_RATE):
        self.sample_rate = sample_rate
        self._stream: Optional[sd.InputStream] = None
        self._queue: queue.Queue = queue.Queue()
        self._callback: Optional[Callable] = None
        self._running = False

    def start(self, callback: Optional[Callable] = None):
        if self._running:
            return
        self._callback = callback
        self._running = True

        def audio_callback(indata, frames, time_info, status):
            if status:
                return
            block = indata.copy()
            if self._callback:
                self._callback(block)
            self._queue.put(block)

        self._stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=CHANNELS,
            dtype=DTYPE,
            blocksize=BLOCK_SIZE,
            callback=audio_callback,
        )
        self._stream.start()

    def stop(self):
        if not self._running:
            return
        self._running = False
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        while not self._queue.empty():
            self._queue.get_nowait()

    def read_block(self) -> np.ndarray:
        return self._queue.get()

    def read_silence_detected(
        self, silence_threshold: float = 0.01, min_silence_blocks: int = 15,
        max_duration: float = 30.0,
    ) -> np.ndarray:
        frames = []
        silent_blocks = 0
        start_time = time.time()

        while silent_blocks < min_silence_blocks:
            if time.time() - start_time > max_duration:
                break
            try:
                block = self._queue.get(timeout=0.5)
            except queue.Empty:
                continue
            frames.append(block)
            level = np.abs(block).mean()
            if level < silence_threshold:
                silent_blocks += 1
            else:
                silent_blocks = 0

        return np.concatenate(frames) if len(frames) > 1 else frames[0] if frames else np.array([], dtype=DTYPE)

    @staticmethod
    def list_devices():
        return sd.query_devices()

    @staticmethod
    def list_mics():
        return [(i, d['name']) for i, d in enumerate(sd.query_devices()) if d['max_input_channels'] > 0]
