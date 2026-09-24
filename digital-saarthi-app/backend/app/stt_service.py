"""
Speech-to-Text (STT) Service for Digital Saarthi

Handles audio file validation, transcription via OpenAI Whisper or SpeechRecognition,
language detection, and confidence scoring.
"""

import io
import logging
import time
import os
from typing import Dict, Any, Optional, Tuple

try:
    from pydub import AudioSegment
except ImportError:
    AudioSegment = None

try:
    import speech_recognition as sr
except ImportError:
    sr = None

try:
    from openai import OpenAI
    openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
except (ImportError, ValueError):
    openai_client = None

logger = logging.getLogger(__name__)

# Audio validation constants
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
MIN_DURATION = 0.5  # 0.5 seconds
MAX_DURATION = 300  # 5 minutes
SUPPORTED_FORMATS = {"wav", "mp3", "m4a", "flac"}
ALLOWED_MIME_TYPES = {"audio/wav", "audio/mpeg", "audio/mp4", "audio/x-flac", "audio/flac"}

# Magic bytes for audio format detection
MAGIC_BYTES = {
    b"RIFF": "wav",
    b"ID3": "mp3",
    b"\xff\xfb": "mp3",
    b"\xff\xfa": "mp3",
    b"ftyp": "m4a",
    b"fLaC": "flac",
}


def validate_audio_file(file_bytes: bytes, content_type: str) -> Tuple[bool, Optional[str]]:
    """
    Validate audio file: MIME type, magic bytes, size.
    Returns (is_valid, error_message)
    """
    # Check file size
    if len(file_bytes) == 0:
        return False, "Audio file is empty"

    if len(file_bytes) > MAX_FILE_SIZE:
        return False, f"Audio file exceeds 10 MB limit"

    # Check MIME type
    if content_type not in ALLOWED_MIME_TYPES:
        return False, f"Invalid MIME type for audio file. Expected audio/*, got {content_type}"

    # Check magic bytes
    valid_magic = False
    for magic, fmt in MAGIC_BYTES.items():
        if file_bytes.startswith(magic):
            valid_magic = True
            break

    if not valid_magic:
        return False, "Audio file corrupted or unreadable (invalid header or format)"

    return True, None


def get_audio_duration(audio_bytes: bytes, content_type: str) -> Optional[float]:
    """
    Extract audio duration using pydub.
    Returns duration in seconds or None if unable to determine.
    """
    if not AudioSegment:
        logger.warning("pydub not available, cannot extract duration")
        return None

    try:
        # Map MIME type to pydub format
        format_map = {
            "audio/wav": "wav",
            "audio/mpeg": "mp3",
            "audio/mp4": "m4a",
            "audio/x-flac": "flac",
            "audio/flac": "flac",
        }
        fmt = format_map.get(content_type, "wav")

        # Load audio from bytes
        audio = AudioSegment.from_file(io.BytesIO(audio_bytes), format=fmt)
        duration = len(audio) / 1000.0  # pydub returns milliseconds
        return duration
    except Exception as e:
        logger.warning(f"Failed to extract audio duration: {e.__class__.__name__}")
        return None


def detect_silence(audio_bytes: bytes, content_type: str, threshold_ratio: float = 0.9) -> bool:
    """
    Detect if audio is mostly silent (>90% silence).
    Returns True if audio is silent.
    """
    if not AudioSegment:
        logger.warning("pydub not available, cannot detect silence")
        return False

    try:
        format_map = {
            "audio/wav": "wav",
            "audio/mpeg": "mp3",
            "audio/mp4": "m4a",
            "audio/x-flac": "flac",
            "audio/flac": "flac",
        }
        fmt = format_map.get(content_type, "wav")

        audio = AudioSegment.from_file(io.BytesIO(audio_bytes), format=fmt)

        # Simple energy-based silence detection
        # Calculate RMS (Root Mean Square) for energy
        if audio.rms == 0:
            # No audio signal at all
            return True

        # Threshold: if average power is very low, consider silent
        # This is a heuristic check
        silent_samples = 0
        for sample in audio.get_array_of_samples():
            if abs(sample) < 100:  # Low amplitude threshold
                silent_samples += 1

        silence_ratio = silent_samples / max(len(audio.get_array_of_samples()), 1)
        return silence_ratio > threshold_ratio

    except Exception as e:
        logger.warning(f"Silence detection failed: {e.__class__.__name__}")
        return False


def transcribe_with_openai(audio_bytes: bytes, language_hint: str) -> Tuple[str, float]:
    """
    Transcribe using OpenAI Whisper API.
    Returns (transcribed_text, confidence)
    """
    if not openai_client:
        logger.warning("OpenAI client not configured")
        return "", 0.0

    try:
        # Save to temporary BytesIO buffer
        audio_buffer = io.BytesIO(audio_bytes)
        audio_buffer.name = "audio.wav"

        response = openai_client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_buffer,
            language=language_hint if language_hint in ["en", "hi"] else None,
            temperature=0,  # Deterministic
        )

        text = response.text or ""
        # Whisper doesn't return confidence, use heuristic: longer text = higher confidence
        confidence = min(0.95, 0.7 + (len(text) / 1000))
        return text, confidence

    except Exception as e:
        logger.warning(f"OpenAI Whisper transcription failed: {e.__class__.__name__}")
        return "", 0.0


def transcribe_with_speech_recognition(audio_bytes: bytes, language_hint: str) -> Tuple[str, float]:
    """
    Transcribe using SpeechRecognition library (Google SR).
    Returns (transcribed_text, confidence)
    Lower confidence (0.6) to indicate fallback backend.
    """
    if not sr:
        logger.warning("SpeechRecognition not available")
        return "", 0.0

    try:
        recognizer = sr.Recognizer()

        # Load audio from bytes
        audio_buffer = io.BytesIO(audio_bytes)
        try:
            audio_data = sr.AudioFile(audio_buffer)
        except Exception:
            # If AudioFile fails, try alternative
            logger.warning("SpeechRecognition AudioFile failed, attempting raw audio")
            return "", 0.0

        with audio_data as source:
            audio = recognizer.record(source)

        # Try to recognize with language hint
        try:
            if language_hint == "hi":
                text = recognizer.recognize_google(audio, language="hi-IN")
            else:
                text = recognizer.recognize_google(audio, language="en-US")
        except sr.UnknownValueError:
            logger.warning("Google Speech Recognition: could not understand audio")
            return "", 0.0
        except sr.RequestError as e:
            logger.warning(f"Google Speech Recognition request failed: {e}")
            return "", 0.0

        # Lower confidence for fallback backend
        confidence = min(0.85, 0.6 + (len(text) / 1500))
        return text, confidence

    except Exception as e:
        logger.warning(f"SpeechRecognition transcription failed: {e.__class__.__name__}")
        return "", 0.0


def transcribe_audio(audio_bytes: bytes, language_hint: str = "auto") -> Dict[str, Any]:
    """
    Main STT entry point.
    Tries OpenAI Whisper first, falls back to SpeechRecognition.
    Returns dict with transcribed_text, detected_language, confidence, duration, processing_time.
    """
    start_time = time.time()

    # Validate file
    # Try to infer MIME type from magic bytes
    inferred_mime = "audio/wav"  # default
    for magic, fmt in MAGIC_BYTES.items():
        if audio_bytes.startswith(magic):
            if fmt == "wav":
                inferred_mime = "audio/wav"
            elif fmt == "mp3":
                inferred_mime = "audio/mpeg"
            elif fmt == "m4a":
                inferred_mime = "audio/mp4"
            elif fmt == "flac":
                inferred_mime = "audio/flac"
            break

    is_valid, error_msg = validate_audio_file(audio_bytes, inferred_mime)
    if not is_valid:
        logger.error(f"Audio validation failed: {error_msg}")
        return {
            "transcribed_text": "",
            "detected_language": "unknown",
            "stt_confidence": 0.0,
            "duration_seconds": 0.0,
            "processing_time_ms": int((time.time() - start_time) * 1000),
            "is_silent": False,
            "error": error_msg,
        }

    # Get duration
    duration = get_audio_duration(audio_bytes, inferred_mime) or 0.0

    # Check duration limits
    if duration < MIN_DURATION and duration > 0:
        error = f"Audio file too short (minimum 0.5 seconds)"
        logger.warning(error)
        return {
            "transcribed_text": "",
            "detected_language": "unknown",
            "stt_confidence": 0.0,
            "duration_seconds": duration,
            "processing_time_ms": int((time.time() - start_time) * 1000),
            "is_silent": False,
            "error": error,
        }

    if duration > MAX_DURATION:
        error = f"Audio file too long (maximum 5 minutes)"
        logger.warning(error)
        return {
            "transcribed_text": "",
            "detected_language": "unknown",
            "stt_confidence": 0.0,
            "duration_seconds": duration,
            "processing_time_ms": int((time.time() - start_time) * 1000),
            "is_silent": False,
            "error": error,
        }

    # Detect silence
    is_silent = detect_silence(audio_bytes, inferred_mime)
    if is_silent:
        logger.warning("Audio detected as silent")
        return {
            "transcribed_text": "",
            "detected_language": "unknown",
            "stt_confidence": 0.0,
            "duration_seconds": duration,
            "processing_time_ms": int((time.time() - start_time) * 1000),
            "is_silent": True,
        }

    # Try transcription: OpenAI first, fallback to SR
    text = ""
    confidence = 0.0
    provider = "none"

    if openai_client:
        text, confidence = transcribe_with_openai(audio_bytes, language_hint)
        if text:
            provider = "openai_whisper"

    if not text and sr:
        text, confidence = transcribe_with_speech_recognition(audio_bytes, language_hint)
        if text:
            provider = "speech_recognition"

    if not text:
        logger.error("All STT backends failed")
        return {
            "transcribed_text": "",
            "detected_language": "unknown",
            "stt_confidence": 0.0,
            "duration_seconds": duration,
            "processing_time_ms": int((time.time() - start_time) * 1000),
            "is_silent": False,
            "error": "Speech recognition service unavailable",
        }

    # Simple language detection: check for Hindi characters
    detected_lang = "en"
    if any(ord(c) >= 0x0900 and ord(c) <= 0x097F for c in text):
        detected_lang = "hi"

    # Override if language_hint is specific
    if language_hint in ["en", "hi"]:
        detected_lang = language_hint

    return {
        "transcribed_text": text,
        "detected_language": detected_lang,
        "stt_confidence": confidence,
        "duration_seconds": duration,
        "processing_time_ms": int((time.time() - start_time) * 1000),
        "is_silent": False,
        "stt_provider": provider,
    }
