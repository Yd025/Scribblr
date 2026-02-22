"""
Continuous background audio capture with silence-aware buffer draining.

Records from the microphone in a background thread. The main loop calls
drain_buffer() to grab all accumulated audio. Audio keeps recording even
while the caller is busy (writing, pausing, calling APIs).
"""

import threading
import io
import wave
import numpy as np
import sounddevice as sd
from python import config


class AudioCapture:
    def __init__(self):
        self._buffer = np.array([], dtype=np.float32)
        self._lock = threading.Lock()
        self._running = False
        self._stream = None

    def start(self):
        self._running = True
        self._stream = sd.InputStream(
            samplerate=config.SAMPLE_RATE,
            channels=config.CHANNELS,
            dtype="float32",
            callback=self._audio_callback,
            blocksize=int(config.SAMPLE_RATE * 0.1),
        )
        self._stream.start()

    def stop(self):
        self._running = False
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None

    def _audio_callback(self, indata, frames, time_info, status):
        if not self._running:
            return
        mono = indata[:, 0] if indata.ndim > 1 else indata.flatten()
        with self._lock:
            self._buffer = np.concatenate([self._buffer, mono])

    def drain_buffer(self) -> bytes | None:
        """Return all buffered audio as WAV bytes and clear the buffer.

        Waits until at least AUDIO_MIN_CHUNK_SEC of audio has accumulated.
        Tries to cut at a silence boundary so we don't chop mid-sentence.
        Returns None if not enough audio yet.
        """
        with self._lock:
            min_samples = int(config.SAMPLE_RATE * config.AUDIO_MIN_CHUNK_SEC)
            if len(self._buffer) < min_samples:
                return None

            audio = self._buffer.copy()
            self._buffer = np.array([], dtype=np.float32)

        cut = self._find_silence_cut(audio)
        if cut is not None and cut > min_samples:
            leftover = audio[cut:]
            audio = audio[:cut]
            with self._lock:
                self._buffer = np.concatenate([leftover, self._buffer])

        return self._to_wav_bytes(audio)

    def _find_silence_cut(self, audio: np.ndarray) -> int | None:
        """Find the last silence boundary in the audio, searching from the end."""
        window = int(config.SAMPLE_RATE * 0.1)
        silence_samples = int(config.SAMPLE_RATE * config.SILENCE_DURATION)
        search_start = max(0, len(audio) - int(config.SAMPLE_RATE * 5))

        for i in range(len(audio) - window, search_start, -window):
            chunk_rms = np.sqrt(np.mean(audio[i : i + window] ** 2))
            if chunk_rms < config.SILENCE_THRESHOLD:
                count = 0
                j = i
                while j >= search_start:
                    rms = np.sqrt(np.mean(audio[j : j + window] ** 2))
                    if rms < config.SILENCE_THRESHOLD:
                        count += window
                        j -= window
                    else:
                        break
                if count >= silence_samples:
                    return i + window
        return None

    def _to_wav_bytes(self, audio: np.ndarray) -> bytes:
        pcm = (audio * 32767).astype(np.int16)
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(config.CHANNELS)
            wf.setsampwidth(2)
            wf.setframerate(config.SAMPLE_RATE)
            wf.writeframes(pcm.tobytes())
        return buf.getvalue()

    def record_seconds(self, duration: float) -> bytes:
        """Record for exactly `duration` seconds and return WAV bytes.
        Useful for testing — does not use the background buffer.
        """
        samples = int(config.SAMPLE_RATE * duration)
        print(f"Recording for {duration}s ...")
        audio = sd.rec(
            samples,
            samplerate=config.SAMPLE_RATE,
            channels=config.CHANNELS,
            dtype="float32",
        )
        sd.wait()
        print("Recording done.")
        return self._to_wav_bytes(audio.flatten())
