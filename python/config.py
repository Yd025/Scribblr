import os
import math
from pathlib import Path

# ── Load .env file automatically ──────────────────────────────────────
_env_file = Path(__file__).resolve().parent.parent / ".env"
if _env_file.exists():
    for line in _env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())

# ── API Keys (set via .env file or environment variables) ─────────────
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

# ── Board Dimensions (mm) ─────────────────────────────────────────────
BOARD_WIDTH = 400
BOARD_HEIGHT = 400

# ── Character Dimensions (mm) ─────────────────────────────────────────
CHAR_HEIGHT = 40
CHAR_WIDTH = 26
CHAR_SPACING = 7
LINE_SPACING = 15

# ── Motion ────────────────────────────────────────────────────────────
WRITE_FEEDRATE = 1500      # mm/min
RAPID_FEEDRATE = 3000      # mm/min for non-writing moves

# ── Pacing ────────────────────────────────────────────────────────────
PAUSE_AFTER_WRITE = 15     # seconds to wait after writing before next cycle
AUDIO_MIN_CHUNK_SEC = 5    # minimum seconds of audio before processing

# ── Audio ─────────────────────────────────────────────────────────────
SAMPLE_RATE = 16000        # Hz
CHANNELS = 1
SILENCE_THRESHOLD = 0.02   # RMS below this = silence
SILENCE_DURATION = 1.5     # seconds of silence to consider a pause

# ── Communication ─────────────────────────────────────────────────────
SERIAL_PORT = "/dev/cu.usbmodemSN234567892"
SERIAL_BAUD = 115200
WIFI_HOST = "192.168.1.100"
WIFI_PORT = 23
COMM_MODE = "serial"       # "serial", "wifi", or "dummy"

# ── Computed at import time ───────────────────────────────────────────
MAX_CHARS_PER_LINE = math.floor(BOARD_WIDTH / (CHAR_WIDTH + CHAR_SPACING))
MAX_LINES = math.floor(BOARD_HEIGHT / (CHAR_HEIGHT + LINE_SPACING))
