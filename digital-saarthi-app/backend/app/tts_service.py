"""
Stage 6: Text-to-Speech Service

Converts eligibility explanations to MP3 audio (Hindi + English).

Audio Quality:
- Sample rate: 16 kHz (good for voice clarity)
- Bitrate: 128 kbps (compact, accessible)
- Format: MP3 (widely supported)
- Speech rate: 0.9x (slightly slower for elderly users)
- Pitch: natural (not robotic)

Fallback Strategy:
- Primary: Google Cloud Text-to-Speech (professional quality, multilingual)
- Fallback: pyttsx3 (offline, simple, pure Python)
- If both fail: return None gracefully (UI shows text without audio)
"""

import logging
import io
import hashlib
from typing import Optional, Dict, Any
import os
from datetime import datetime

logger = logging.getLogger(__name__)

# Try to import Google TTS
try:
    from google.cloud import texttospeech
    HAS_GOOGLE_TTS = True
except ImportError:
    HAS_GOOGLE_TTS = False
    logger.warning("Google Cloud TTS not available. Using fallback only.")

# Try to import pyttsx3
try:
    import pyttsx3
    HAS_PYTTSX3 = True
except ImportError:
    HAS_PYTTSX3 = False
    logger.warning("pyttsx3 not available. Some TTS functionality limited.")


class TTSService:
    """Safe TTS service for generating audio explanations."""

    # Voice mapping for Google Cloud TTS
    GOOGLE_VOICES = {
        'hi': {
            'female': 'hi-IN-Neural2-A',
            'male': 'hi-IN-Neural2-B',
        },
        'en': {
            'female': 'en-IN-Neural2-A',
            'male': 'en-IN-Neural2-B',
        }
    }

    # pyttsx3 voice configuration
    PYTTSX3_VOICES = {
        'hi': {'female': 'hindi-female', 'male': 'hindi-male'},
        'en': {'female': 'english-female', 'male': 'english-male'},
    }

    def __init__(self, enable_google: bool = True, enable_fallback: bool = True):
        """
        Initialize TTS service with optional Google Cloud and pyttsx3.

        Args:
            enable_google: Try to use Google Cloud TTS if available
            enable_fallback: Use pyttsx3 as fallback
        """
        self.enable_google = enable_google and HAS_GOOGLE_TTS
        self.enable_fallback = enable_fallback and HAS_PYTTSX3

        if self.enable_google:
            try:
                self.google_client = texttospeech.TextToSpeechClient()
                logger.info("Google Cloud TTS client initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Google TTS: {e}")
                self.enable_google = False

        if self.enable_fallback:
            try:
                # Initialize pyttsx3 engine
                self.pyttsx3_engine = pyttsx3.init()
                self.pyttsx3_engine.setProperty('rate', 150)  # Slow for elderly
                logger.info("pyttsx3 engine initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize pyttsx3: {e}")
                self.enable_fallback = False

        if not self.enable_google and not self.enable_fallback:
            logger.error("No TTS backend available. Audio generation will fail.")

    def synthesize(
        self,
        text: str,
        language: str = "hi",
        voice_type: str = "female"
    ) -> Optional[Dict[str, Any]]:
        """
        Convert text to speech.

        Args:
            text: Text to synthesize
            language: "en" or "hi"
            voice_type: "female" or "male"

        Returns:
            Dict with audio_bytes, duration, provider, etc. or None if failed
        """
        if not text or len(text.strip()) == 0:
            raise ValueError("Text cannot be empty")

        # Normalize language code
        lang_code = 'hi-IN' if language.startswith('hi') else 'en-IN'
        lang_short = 'hi' if language.startswith('hi') else 'en'

        # Try Google TTS first
        if self.enable_google:
            result = self._synthesize_google(text, lang_code, lang_short, voice_type)
            if result:
                return result

        # Fallback to pyttsx3
        if self.enable_fallback:
            result = self._synthesize_pyttsx3(text, lang_short, voice_type)
            if result:
                return result

        # Both failed
        logger.error("All TTS backends failed")
        return None

    def _synthesize_google(
        self,
        text: str,
        lang_code: str,
        lang_short: str,
        voice_type: str
    ) -> Optional[Dict[str, Any]]:
        """
        Synthesize using Google Cloud TTS.

        Args:
            text: Text to synthesize
            lang_code: Language code (hi-IN, en-IN)
            lang_short: Short language code (hi, en)
            voice_type: "female" or "male"

        Returns:
            Audio result dict or None if failed
        """
        try:
            # Get voice
            voice_name = self.GOOGLE_VOICES.get(lang_short, {}).get(voice_type)
            if not voice_name:
                logger.warning(f"Voice not found for {lang_short}-{voice_type}")
                return None

            # Set up request
            synthesis_input = texttospeech.SynthesisInput(text=text)
            voice = texttospeech.VoiceSelectionParams(
                language_code=lang_code,
                name=voice_name,
            )
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3,
                sample_rate_hertz=16000,
                pitch=0.0,  # Natural pitch
                speaking_rate=0.9,  # 10% slower for elderly
            )

            # Call API
            response = self.google_client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config
            )

            # Calculate duration (rough estimate: 60 chars ≈ 1 second)
            duration = max(0.5, len(text) / 140)

            return {
                'audio_bytes': response.audio_content,
                'duration_seconds': duration,
                'provider': 'google_tts',
                'language': lang_short,
                'encoding': 'audio/mpeg',
                'sample_rate': 16000,
                'bitrate': '128k',
                'confidence': 0.95,
                'generated_at': datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.warning(f"Google TTS failed: {e}")
            return None

    def _synthesize_pyttsx3(
        self,
        text: str,
        lang_short: str,
        voice_type: str
    ) -> Optional[Dict[str, Any]]:
        """
        Synthesize using pyttsx3 fallback.

        Args:
            text: Text to synthesize
            lang_short: Language code (hi, en)
            voice_type: "female" or "male"

        Returns:
            Audio result dict or None if failed
        """
        try:
            # Reset engine
            self.pyttsx3_engine.setProperty('rate', 150)  # Slow
            self.pyttsx3_engine.setProperty('volume', 1.0)

            # Save to bytes buffer
            audio_buffer = io.BytesIO()
            self.pyttsx3_engine.save_to_file(text, audio_buffer)
            self.pyttsx3_engine.runAndWait()

            # Get audio bytes
            audio_bytes = audio_buffer.getvalue()
            if not audio_bytes:
                # pyttsx3 doesn't support direct WAV to bytes easily
                # Generate a minimal WAV header with silence as fallback
                logger.warning("pyttsx3 audio generation produced no output")
                return None

            # Calculate duration
            duration = max(0.5, len(text) / 140)

            return {
                'audio_bytes': audio_bytes,
                'duration_seconds': duration,
                'provider': 'pyttsx3',
                'language': lang_short,
                'encoding': 'audio/wav',
                'sample_rate': 16000,
                'bitrate': '128k',
                'confidence': 0.70,
                'generated_at': datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.warning(f"pyttsx3 TTS failed: {e}")
            return None

    def synthesize_bilingual(
        self,
        text_en: str,
        text_hi: str,
        voice_type: str = "female"
    ) -> Optional[Dict[str, Any]]:
        """
        Generate both English and Hindi audio.

        Args:
            text_en: English text
            text_hi: Hindi text
            voice_type: "female" or "male"

        Returns:
            Dict with audio_en and audio_hi, or None if both fail
        """
        result_en = self.synthesize(text_en, language='en', voice_type=voice_type)
        result_hi = self.synthesize(text_hi, language='hi', voice_type=voice_type)

        if not result_en or not result_hi:
            logger.warning("Bilingual synthesis failed")
            return None

        return {
            'audio_en': result_en,
            'audio_hi': result_hi,
            'provider': result_en['provider'],
            'generated_at': datetime.utcnow().isoformat()
        }

    def generate_audio_url(self, audio_hash: str, language: str = "hi") -> str:
        """
        Generate stable URL for audio file.

        Args:
            audio_hash: Hash of content (for uniqueness)
            language: "en" or "hi"

        Returns:
            Relative URL path
        """
        return f"/api/audio/{language}-{audio_hash}.mp3"

    def hash_text(self, text: str) -> str:
        """
        Generate stable hash of text for URL.

        Args:
            text: Text to hash

        Returns:
            Hex hash string (first 8 chars)
        """
        return hashlib.md5(text.encode()).hexdigest()[:8]


# Initialize global TTS service
tts_service: Optional[TTSService] = None


def init_tts_service(enable_google: bool = True, enable_fallback: bool = True):
    """
    Initialize global TTS service.

    Args:
        enable_google: Try to use Google Cloud TTS
        enable_fallback: Use pyttsx3 as fallback
    """
    global tts_service
    tts_service = TTSService(enable_google=enable_google, enable_fallback=enable_fallback)
    logger.info(f"TTS service initialized: google={tts_service.enable_google}, "
               f"fallback={tts_service.enable_fallback}")
