"""
Concurrent demo pipeline.

Three threads run simultaneously:
  1. Audio capture  — records from mic into a buffer (already threaded via sounddevice)
  2. Processing loop — drains audio buffer, transcribes (ElevenLabs), summarizes (Gemini),
                       and pushes text onto a write queue
  3. Writing loop    — pulls text from the queue, generates G-code, sends to machine

When the user presses ENTER, audio stops. The processing thread does one
final drain, then signals the writing thread to finish its queue and exit.
"""

import time
import queue
import threading
import argparse
import sys

from python import config
from python.audio_capture import AudioCapture
from python.elevenlabs_stt import transcribe
from python.gemini_api import summarize
from python.text_to_gcode import TextToGCode
from python import machine_comm

_SENTINEL = None  # pushed onto write_queue to signal "no more items"


def processing_loop(
    capture: AudioCapture,
    write_queue: queue.Queue,
    stop_event: threading.Event,
    written_history: list[str],
    history_lock: threading.Lock,
):
    """Periodically drain audio, transcribe, summarize, and enqueue text to write."""
    while not stop_event.is_set():
        stop_event.wait(timeout=config.AUDIO_MIN_CHUNK_SEC)
        _process_one_chunk(capture, write_queue, written_history, history_lock)

    # Final drain after stop signal
    print("[PROCESS] Final drain ...")
    time.sleep(0.5)
    _process_one_chunk(capture, write_queue, written_history, history_lock, final=True)

    write_queue.put(_SENTINEL)
    print("[PROCESS] Done — no more chunks to process.")


def _process_one_chunk(
    capture: AudioCapture,
    write_queue: queue.Queue,
    written_history: list[str],
    history_lock: threading.Lock,
    final: bool = False,
):
    wav_bytes = capture.drain_buffer()
    if wav_bytes is None:
        if final:
            print("[PROCESS] (no remaining audio)")
        return

    audio_len = len(wav_bytes) / (config.SAMPLE_RATE * 2)  # rough seconds
    print(f"[PROCESS] Transcribing {audio_len:.1f}s of audio ...")

    try:
        transcript = transcribe(wav_bytes)
    except Exception as e:
        print(f"[PROCESS] Transcription error: {e}")
        return

    if not transcript:
        print("[PROCESS] (no speech detected)")
        return
    print(f'[PROCESS] Transcript: "{transcript[:100]}{"..." if len(transcript) > 100 else ""}"')

    with history_lock:
        lines_remaining = config.MAX_LINES - len(written_history)
        history_snapshot = list(written_history)

    if lines_remaining <= 0:
        print("[PROCESS] Board is full — skipping until erased.")
        return

    try:
        board_text = summarize(transcript, history_snapshot, lines_remaining)
    except Exception as e:
        print(f"[PROCESS] Summarization error: {e}")
        return

    if board_text is None:
        print("[PROCESS] (nothing worth writing)")
        return

    print(f'[PROCESS] Gemini says: "{board_text}"')
    write_queue.put(board_text)


def writing_loop(
    write_queue: queue.Queue,
    gcode_gen: TextToGCode,
    machine: machine_comm.MachineConnection,
    written_history: list[str],
    history_lock: threading.Lock,
):
    """Pull text from the queue, generate G-code, send to the machine."""
    while True:
        try:
            text = write_queue.get(timeout=1)
        except queue.Empty:
            continue

        if text is _SENTINEL:
            # Drain any remaining items before exiting
            while not write_queue.empty():
                remaining = write_queue.get_nowait()
                if remaining is _SENTINEL:
                    break
                _write_text(remaining, gcode_gen, machine, written_history, history_lock)
            print("[WRITE]   Queue empty. Done.")
            break

        _write_text(text, gcode_gen, machine, written_history, history_lock)


def _write_text(
    text: str,
    gcode_gen: TextToGCode,
    machine: machine_comm.MachineConnection,
    written_history: list[str],
    history_lock: threading.Lock,
):
    print(f'[WRITE]   Writing: "{text}"')
    commands = gcode_gen.convert(text)
    for cmd in commands:
        machine.send(cmd)

    with history_lock:
        for line in text.splitlines():
            stripped = line.strip()
            if stripped:
                written_history.append(stripped)

    print("[WRITE]   Finished.")


def main():
    parser = argparse.ArgumentParser(description="Whiteboard Note-Writer")
    parser.add_argument(
        "--comm",
        choices=["serial", "wifi", "dummy"],
        default=config.COMM_MODE,
        help="Communication mode (default: %(default)s)",
    )
    parser.add_argument(
        "--port",
        type=str,
        default=None,
        help="Serial port to use (e.g. /dev/cu.usbmodem1101)",
    )
    args = parser.parse_args()

    print("=== Whiteboard Note-Writer ===")
    print(f"Board: {config.BOARD_WIDTH}x{config.BOARD_HEIGHT}mm | "
          f"{config.MAX_CHARS_PER_LINE} chars/line, {config.MAX_LINES} lines")
    print(f"Comm: {args.comm}")
    print("Press ENTER to stop listening.\n")

    capture = AudioCapture()
    gcode_gen = TextToGCode()
    machine = machine_comm.connect(args.comm, port=args.port)

    write_queue: queue.Queue = queue.Queue()
    stop_event = threading.Event()
    written_history: list[str] = []
    history_lock = threading.Lock()

    capture.start()
    print("[LISTEN]  Recording ...\n")

    proc_thread = threading.Thread(
        target=processing_loop,
        args=(capture, write_queue, stop_event, written_history, history_lock),
        daemon=True,
    )
    write_thread = threading.Thread(
        target=writing_loop,
        args=(write_queue, gcode_gen, machine, written_history, history_lock),
        daemon=True,
    )

    proc_thread.start()
    write_thread.start()

    try:
        input()  # blocks until ENTER
    except (KeyboardInterrupt, EOFError):
        pass

    print("\n[LISTEN]  Stopped.")
    capture.stop()
    stop_event.set()

    proc_thread.join(timeout=30)
    write_thread.join(timeout=60)

    machine.close()

    print()
    print("── Final board state ───────────────────────────────")
    with history_lock:
        if written_history:
            for line in written_history:
                print(f"  | {line}")
        else:
            print("  (nothing was written)")
    print("────────────────────────────────────────────────────")


if __name__ == "__main__":
    main()
