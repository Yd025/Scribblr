"""
Test audio capture — records a short clip and plays it back.
Verifies the microphone and sounddevice are working.

Usage:
    python -m tests.test_audio [--duration 5]
"""

import argparse
import numpy as np
import sounddevice as sd
import wave
import io

from python.audio_capture import AudioCapture


def main():
    parser = argparse.ArgumentParser(description="Test audio capture")
    parser.add_argument("--duration", type=float, default=5, help="Seconds to record")
    parser.add_argument("--save", type=str, default=None, help="Save WAV to this file")
    args = parser.parse_args()

    capture = AudioCapture()
    wav_bytes = capture.record_seconds(args.duration)

    print(f"Captured {len(wav_bytes)} bytes of WAV audio")

    if args.save:
        with open(args.save, "wb") as f:
            f.write(wav_bytes)
        print(f"Saved to {args.save}")

    # Quick stats
    buf = io.BytesIO(wav_bytes)
    with wave.open(buf, "rb") as wf:
        frames = wf.getnframes()
        rate = wf.getframerate()
        data = np.frombuffer(wf.readframes(frames), dtype=np.int16).astype(np.float32)
        rms = np.sqrt(np.mean((data / 32767) ** 2))
        peak = np.max(np.abs(data / 32767))
        print(f"  Samples: {frames}, Rate: {rate}Hz, Duration: {frames/rate:.1f}s")
        print(f"  RMS: {rms:.4f}, Peak: {peak:.4f}")

    print("\nPlaying back ...")
    buf.seek(0)
    with wave.open(buf, "rb") as wf:
        audio = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16)
        sd.play(audio, samplerate=wf.getframerate())
        sd.wait()

    print("Done.")


if __name__ == "__main__":
    main()
