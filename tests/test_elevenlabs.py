"""
Test ElevenLabs Scribe v2 transcription.
Records audio (or loads a WAV file) and prints the transcript.

Usage:
    python -m tests.test_elevenlabs --duration 10
    python -m tests.test_elevenlabs --file lecture_clip.wav
"""

import argparse

from python.audio_capture import AudioCapture
from python.elevenlabs_stt import transcribe


def main():
    parser = argparse.ArgumentParser(description="Test ElevenLabs transcription")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--duration", type=float, help="Record for N seconds")
    group.add_argument("--file", type=str, help="Path to a WAV file")
    args = parser.parse_args()

    if args.file:
        with open(args.file, "rb") as f:
            wav_bytes = f.read()
        print(f"Loaded {args.file} ({len(wav_bytes)} bytes)")
    else:
        capture = AudioCapture()
        wav_bytes = capture.record_seconds(args.duration)

    print("\nSending to ElevenLabs Scribe v2 ...")
    transcript = transcribe(wav_bytes)

    print("\n── Transcript ──────────────────────────────────────")
    print(transcript if transcript else "(empty — no speech detected)")
    print("────────────────────────────────────────────────────\n")


if __name__ == "__main__":
    main()
