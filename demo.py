"""
Live demo — fullscreen chalkboard display + optional serial output.

The window animates each stroke in real-time at the same speed as the
physical machine. AirPlay this window to an iPad for the judges.

Usage:
    python3 demo.py                          # display only, type text manually
    python3 demo.py --text "HELLO WORLD"     # draw specific text
    python3 demo.py --serial                 # also send to machine via serial
    python3 demo.py --listen                 # full pipeline: mic → AI → draw
"""

import argparse
import threading
import queue
import time

from python import config
from python.text_to_gcode import TextToGCode
from python.live_display import LiveDisplay


def build_text_mode(display, gcode_gen, text, serial_conn):
    """Generate G-code from text and animate it."""
    commands = gcode_gen.convert(text)
    print(f"Drawing {len(commands)} G-code commands for: {text!r}")
    display.execute_commands(commands, serial_conn=serial_conn)


def build_listen_mode(display, gcode_gen, serial_conn):
    """Full pipeline: audio → transcribe → summarize → draw."""
    from python.audio_capture import AudioCapture
    from python.elevenlabs_stt import transcribe
    from python.gemini_api import summarize

    text_queue = queue.Queue()
    stop_event = threading.Event()
    lines_written = []

    def processing_loop():
        audio = AudioCapture()
        audio.start()
        print("[LISTEN] Recording ... press Ctrl+C to stop")

        while not stop_event.is_set():
            chunk = audio.drain_buffer()
            if chunk is None:
                time.sleep(0.5)
                continue

            try:
                transcript = transcribe(chunk)
            except Exception as e:
                print(f"[STT] Error: {e}")
                continue

            if not transcript or len(transcript.strip()) < 5:
                continue

            print(f"[HEARD] {transcript[:80]}...")

            _, cy = gcode_gen.get_cursor_position()
            lines_remaining = max(1, int(cy / (config.CHAR_HEIGHT + config.LINE_SPACING)))

            try:
                board_text = summarize(
                    transcript,
                    lines_remaining=lines_remaining,
                    written_history=lines_written,
                )
            except Exception as e:
                print(f"[GEMINI] Error: {e}")
                continue

            if not board_text:
                print("[GEMINI] (nothing worth writing)")
                continue

            print(f"[WRITE] {board_text}")
            lines_written.extend(board_text.splitlines())
            text_queue.put(board_text)

        audio.stop()

    proc_thread = threading.Thread(target=processing_loop, daemon=True)
    proc_thread.start()

    def check_queue():
        try:
            text = text_queue.get_nowait()
            commands = gcode_gen.convert(text)
            display.execute_commands(commands, serial_conn=serial_conn,
                                     on_done=check_queue)
        except queue.Empty:
            if not stop_event.is_set() or not text_queue.empty():
                display.root.after(500, check_queue)

    display.root.after(1000, check_queue)


def main():
    parser = argparse.ArgumentParser(description="Live chalkboard demo")
    parser.add_argument("--text", type=str, default=None,
                        help="Text to draw (default: interactive prompt)")
    parser.add_argument("--serial", action="store_true",
                        help="Also send G-code to machine via serial")
    parser.add_argument("--port", type=str, default=None,
                        help="Serial port override")
    parser.add_argument("--listen", action="store_true",
                        help="Full pipeline: mic → AI → draw")
    parser.add_argument("--windowed", action="store_true",
                        help="Run in a window instead of fullscreen")
    parser.add_argument("--speed", type=float, default=None,
                        help="Animation speed multiplier (default: 1x with --serial, 15x without)")
    args = parser.parse_args()

    serial_conn = None
    if args.serial:
        from python import machine_comm
        serial_conn = machine_comm.connect("serial", port=args.port)

    if not args.serial:
        import math
        config.CHAR_HEIGHT = 20
        config.CHAR_WIDTH = 13
        config.CHAR_SPACING = 4
        config.LINE_SPACING = 7
        config.MAX_CHARS_PER_LINE = math.floor(config.BOARD_WIDTH / (config.CHAR_WIDTH + config.CHAR_SPACING))
        config.MAX_LINES = math.floor(config.BOARD_HEIGHT / (config.CHAR_HEIGHT + config.LINE_SPACING))

    if args.speed is not None:
        speed = args.speed
    elif args.serial:
        speed = 1.0
    else:
        speed = 15.0

    gcode_gen = TextToGCode()
    display = LiveDisplay(fullscreen=not args.windowed, speed=speed)

    mode = "HARDWARE" if args.serial else "SOFTWARE"
    print(f"Mode: {mode} | {config.MAX_CHARS_PER_LINE} chars/line, {config.MAX_LINES} lines | speed: {speed}x")

    if args.listen:
        build_listen_mode(display, gcode_gen, serial_conn)
    elif args.text:
        display.root.after(500, lambda: build_text_mode(
            display, gcode_gen, args.text, serial_conn))
    else:
        text = input("Enter text to draw: ").strip() or "HELLO"
        display.root.after(500, lambda: build_text_mode(
            display, gcode_gen, text, serial_conn))

    print("Display running — press Escape to exit fullscreen, close window to quit")
    display.run()

    if serial_conn:
        serial_conn.close()


if __name__ == "__main__":
    main()
