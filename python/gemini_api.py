"""
Gemini-powered board-aware summarization.

Receives a transcript, the physical board constraints, and a history of
what's already been written. Gemini decides what (if anything) to write
and formats it to fit the board — no presets, no modes.
"""

import time
from google import genai
from google.genai import errors as genai_errors
from python import config

_client = None

GEMINI_MODEL = "gemini-2.5-flash"
MAX_RETRIES = 3

SYSTEM_PROMPT = """\
You are controlling a machine that writes lecture notes on a physical board
for students to read and copy down. You decide what is worth writing.

BOARD CONSTRAINTS:
- Maximum {max_chars} characters per line
- {lines_remaining} empty lines remaining on the board
- Writing is slow and physical — every character costs time

ALREADY ON THE BOARD:
{history}

NEW TRANSCRIPT FROM THE LECTURE:
{transcript}

Write ONLY what deserves to go on the board given your space constraints.
Fit your output to the board — be as detailed as the space allows,
or as terse as the space demands.
Use this format — topic as a heading, then bullet points with hyphens:
  TOPIC
  - key point 1
  - key point 2
If the topic is already on the board, just add new bullet points.
Never repeat anything already on the board.
Each line must be at most {max_chars} characters.
If nothing new or important was said, return NONE."""


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        if not config.GEMINI_API_KEY:
            raise RuntimeError(
                "GEMINI_API_KEY not set. "
                "Export it as an environment variable or set it in config.py"
            )
        _client = genai.Client(api_key=config.GEMINI_API_KEY)
    return _client


def summarize(
    transcript: str,
    written_history: list[str],
    lines_remaining: int | None = None,
) -> str | None:
    """Ask Gemini what should go on the board next.

    Returns the text to write (one or more lines), or None if Gemini
    decides there's nothing worth writing.
    """
    if not transcript.strip():
        return None

    if lines_remaining is None:
        lines_remaining = config.MAX_LINES - len(written_history)
    lines_remaining = max(lines_remaining, 0)

    history_text = "\n".join(written_history) if written_history else "(empty)"

    prompt = SYSTEM_PROMPT.format(
        max_chars=config.MAX_CHARS_PER_LINE,
        lines_remaining=lines_remaining,
        history=history_text,
        transcript=transcript,
    )

    client = _get_client()

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
            )
            break
        except genai_errors.ClientError as e:
            if "429" in str(e) and attempt < MAX_RETRIES:
                wait = 10 * attempt
                print(f"[GEMINI] Rate limited, retrying in {wait}s (attempt {attempt}/{MAX_RETRIES}) ...")
                time.sleep(wait)
            else:
                raise

    text = response.text.strip()

    if text.upper() == "NONE":
        return None

    # Enforce per-line character limit
    lines = []
    for line in text.splitlines():
        line = line.strip()
        if line:
            lines.append(line[: config.MAX_CHARS_PER_LINE])

    if not lines:
        return None

    return "\n".join(lines)
