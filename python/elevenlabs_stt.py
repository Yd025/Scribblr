"""
ElevenLabs Scribe v2 speech-to-text wrapper.
Takes WAV audio bytes, returns the transcribed text string.
"""

from io import BytesIO
from elevenlabs.client import ElevenLabs
from python import config

_client = None


def _get_client() -> ElevenLabs:
    global _client
    if _client is None:
        if not config.ELEVENLABS_API_KEY:
            raise RuntimeError(
                "ELEVENLABS_API_KEY not set. "
                "Export it as an environment variable or set it in config.py"
            )
        _client = ElevenLabs(api_key=config.ELEVENLABS_API_KEY)
    return _client


def transcribe(wav_bytes: bytes) -> str:
    """Transcribe WAV audio bytes using ElevenLabs Scribe v2.

    Returns the transcript as a plain string, or empty string if
    the transcription returned nothing.
    """
    client = _get_client()
    audio_file = BytesIO(wav_bytes)
    audio_file.name = "audio.wav"

    result = client.speech_to_text.convert(
        file=audio_file,
        model_id="scribe_v2",
        language_code="eng",
    )
    text = result.text if hasattr(result, "text") else str(result)
    return text.strip()
