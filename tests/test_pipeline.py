"""
Full end-to-end pipeline test.

Records audio (or loads a WAV file), runs it through:
  1. ElevenLabs transcription
  2. Gemini summarization
  3. G-code generation
  4. G-code visualization (matplotlib)

Prints every intermediate result so you can inspect each stage.

Usage:
    python -m tests.test_pipeline --duration 10
    python -m tests.test_pipeline --file lecture_clip.wav
    python -m tests.test_pipeline --duration 15 --text-only
    python -m tests.test_pipeline --duration 10 --save preview.png
"""

import argparse
import time

from python import config
from python.audio_capture import AudioCapture
from python.elevenlabs_stt import transcribe
from python.gemini_api import summarize
from python.text_to_gcode import TextToGCode
from tests.gcode_visualizer import visualize


def main():
    parser = argparse.ArgumentParser(description="Full pipeline test")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--duration", type=float, help="Record for N seconds")
    group.add_argument("--file", type=str, help="Path to a WAV file")
    parser.add_argument(
        "--text-only",
        action="store_true",
        help="Skip G-code generation and visualization",
    )
    parser.add_argument("--save", type=str, default=None, help="Save preview plot to file")
    args = parser.parse_args()

    print("=" * 56)
    print("  WHITEBOARD NOTE-WRITER — PIPELINE TEST")
    print("=" * 56)
    print(f"  Board: {config.BOARD_WIDTH}x{config.BOARD_HEIGHT}mm")
    print(f"  Chars/line: {config.MAX_CHARS_PER_LINE}  |  Lines: {config.MAX_LINES}")
    print("=" * 56)
    print()

    # ── Step 1: Audio ─────────────────────────────────────────────────
    if args.file:
        with open(args.file, "rb") as f:
            wav_bytes = f.read()
        print(f"[1/4] Loaded audio file: {args.file} ({len(wav_bytes)} bytes)")
    else:
        capture = AudioCapture()
        wav_bytes = capture.record_seconds(args.duration)
        print(f"[1/4] Recorded {args.duration}s of audio ({len(wav_bytes)} bytes)")
    print()

    # ── Step 2: Transcription ─────────────────────────────────────────
    print("[2/4] Transcribing via ElevenLabs Scribe v2 ...")
    t0 = time.time()
    transcript = transcribe(wav_bytes)
    dt = time.time() - t0
    print(f"      ({dt:.1f}s)")
    print()
    print("── TRANSCRIPT ──────────────────────────────────────")
    print(transcript if transcript else "(empty)")
    print("────────────────────────────────────────────────────")
    print()

    if not transcript:
        print("No speech detected. Exiting.")
        return

    # ── Step 3: Summarization ─────────────────────────────────────────
    print("[3/4] Asking Gemini what to write on the board ...")
    t0 = time.time()
    board_text = summarize(transcript, written_history=[], lines_remaining=config.MAX_LINES)
    dt = time.time() - t0
    print(f"      ({dt:.1f}s)")
    print()
    print("── BOARD OUTPUT ────────────────────────────────────")
    if board_text is None:
        print("(NONE — Gemini says nothing worth writing)")
        print("────────────────────────────────────────────────────")
        return
    else:
        for line in board_text.splitlines():
            print(f"  | {line}")
    print("────────────────────────────────────────────────────")
    print()

    if args.text_only:
        print("(--text-only: skipping G-code generation)")
        return

    # ── Step 4: G-code ────────────────────────────────────────────────
    print("[4/4] Generating G-code ...")
    gcode_gen = TextToGCode()
    commands = gcode_gen.convert(board_text)
    print(f"      {len(commands)} G-code commands generated")
    print()

    print("── G-CODE (first 30 lines) ─────────────────────────")
    for cmd in commands[:30]:
        print(f"  {cmd}")
    if len(commands) > 30:
        print(f"  ... ({len(commands) - 30} more)")
    print("────────────────────────────────────────────────────")
    print()

    # ── Visualization ─────────────────────────────────────────────────
    print("Rendering preview ...")
    save = args.save or "preview.png"
    visualize(commands, title=f"Board preview: {board_text!r}", save_path=save, show=not save)

    print("\nDone!")


if __name__ == "__main__":
    main()
