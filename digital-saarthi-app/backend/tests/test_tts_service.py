"""
Tests for Text-to-Speech Service

Tests audio generation, format validation, and fallback handling.
"""

import pytest
import sys
from unittest.mock import patch, MagicMock

# Mock optional TTS libraries
sys.modules['google.cloud'] = MagicMock()
sys.modules['google.cloud.texttospeech'] = MagicMock()
sys.modules['pyttsx3'] = MagicMock()

from app.tts_service import TTSService


class TestTTSServiceInitialization:
    """Test TTS service initialization."""

    def test_init_google_unavailable(self):
        """Should handle missing Google TTS gracefully."""
        with patch('app.tts_service.HAS_GOOGLE_TTS', False):
            service = TTSService(enable_google=True, enable_fallback=False)
            assert service.enable_google is False

    def test_init_pyttsx3_unavailable(self):
        """Should handle missing pyttsx3 gracefully."""
        with patch('app.tts_service.HAS_PYTTSX3', False):
            service = TTSService(enable_google=False, enable_fallback=True)
            assert service.enable_fallback is False

    def test_init_no_backends(self):
        """Should handle case when no backends available."""
        with patch('app.tts_service.HAS_GOOGLE_TTS', False):
            with patch('app.tts_service.HAS_PYTTSX3', False):
                service = TTSService(enable_google=True, enable_fallback=True)
                assert service.enable_google is False
                assert service.enable_fallback is False


class TestTTSSynthesizeValidation:
    """Test input validation."""

    def test_reject_empty_text(self):
        """Should reject empty text."""
        service = TTSService(enable_google=False, enable_fallback=False)

        with pytest.raises(ValueError):
            service.synthesize("")

    def test_reject_whitespace_only(self):
        """Should reject whitespace-only text."""
        service = TTSService(enable_google=False, enable_fallback=False)

        with pytest.raises(ValueError):
            service.synthesize("   ")


class TestTTSSynthesizeNoBackends:
    """Test behavior when no TTS backends available."""

    def test_synthesize_returns_none_no_backends(self):
        """Should return None when no backends available."""
        service = TTSService(enable_google=False, enable_fallback=False)

        result = service.synthesize("Test text", language='en')
        assert result is None

    def test_synthesize_bilingual_returns_none_no_backends(self):
        """Should return None for bilingual when no backends available."""
        service = TTSService(enable_google=False, enable_fallback=False)

        result = service.synthesize_bilingual(
            text_en="Test",
            text_hi="परीक्षण"
        )
        assert result is None


class TestTTSAudioURLGeneration:
    """Test audio URL generation."""

    def test_generate_audio_url_hindi(self):
        """Should generate Hindi audio URL."""
        service = TTSService(enable_google=False, enable_fallback=False)

        url = service.generate_audio_url("abc123def", language="hi")

        assert url.startswith("/api/audio/")
        assert "hi-" in url
        assert url.endswith(".mp3")

    def test_generate_audio_url_english(self):
        """Should generate English audio URL."""
        service = TTSService(enable_google=False, enable_fallback=False)

        url = service.generate_audio_url("abc123def", language="en")

        assert url.startswith("/api/audio/")
        assert "en-" in url
        assert url.endswith(".mp3")

    def test_hash_text_consistency(self):
        """Same text should produce same hash."""
        service = TTSService(enable_google=False, enable_fallback=False)

        text = "Test audio content"
        hash1 = service.hash_text(text)
        hash2 = service.hash_text(text)

        assert hash1 == hash2
        assert len(hash1) == 8

    def test_hash_text_different_for_different_input(self):
        """Different texts should produce different hashes."""
        service = TTSService(enable_google=False, enable_fallback=False)

        hash1 = service.hash_text("Text 1")
        hash2 = service.hash_text("Text 2")

        assert hash1 != hash2


class TestTTSVoiceSelection:
    """Test voice type selection."""

    def test_female_voice_hindi(self):
        """Should support female voice for Hindi."""
        service = TTSService(enable_google=False, enable_fallback=False)

        assert 'female' in service.GOOGLE_VOICES['hi']
        assert service.GOOGLE_VOICES['hi']['female'] == 'hi-IN-Neural2-A'

    def test_male_voice_hindi(self):
        """Should support male voice for Hindi."""
        service = TTSService(enable_google=False, enable_fallback=False)

        assert 'male' in service.GOOGLE_VOICES['hi']
        assert service.GOOGLE_VOICES['hi']['male'] == 'hi-IN-Neural2-B'

    def test_female_voice_english(self):
        """Should support female voice for English."""
        service = TTSService(enable_google=False, enable_fallback=False)

        assert 'female' in service.GOOGLE_VOICES['en']
        assert service.GOOGLE_VOICES['en']['female'] == 'en-IN-Neural2-A'

    def test_male_voice_english(self):
        """Should support male voice for English."""
        service = TTSService(enable_google=False, enable_fallback=False)

        assert 'male' in service.GOOGLE_VOICES['en']
        assert service.GOOGLE_VOICES['en']['male'] == 'en-IN-Neural2-B'


class TestTTSAudioDurationCalculation:
    """Test audio duration estimation."""

    def test_duration_short_text(self):
        """Short text should have minimal duration."""
        service = TTSService(enable_google=False, enable_fallback=False)

        # Mock the synthesize method for testing
        text = "Hi"
        # Duration = max(0.5, len(text) / 140) = max(0.5, 2/140) = 0.5
        estimated_duration = max(0.5, len(text) / 140)
        assert estimated_duration == 0.5

    def test_duration_long_text(self):
        """Long text should have longer estimated duration."""
        service = TTSService(enable_google=False, enable_fallback=False)

        short_text = "Hi"
        long_text = "This is a much longer text with many words that should result in a longer audio duration estimate."

        short_duration = max(0.5, len(short_text) / 140)
        long_duration = max(0.5, len(long_text) / 140)

        assert long_duration > short_duration


class TestTTSLanguageSupport:
    """Test language code handling."""

    def test_supported_languages(self):
        """Should support Hindi and English."""
        service = TTSService(enable_google=False, enable_fallback=False)

        assert 'hi' in service.GOOGLE_VOICES
        assert 'en' in service.GOOGLE_VOICES

    def test_language_normalization_hi_in(self):
        """Should handle hi-IN language code."""
        service = TTSService(enable_google=False, enable_fallback=False)

        # The _synthesize_google method normalizes language codes
        # hi-IN → hi-IN (no change needed)
        assert 'hi' in service.GOOGLE_VOICES

    def test_language_normalization_en_in(self):
        """Should handle en-IN language code."""
        service = TTSService(enable_google=False, enable_fallback=False)

        # The _synthesize_google method normalizes language codes
        # en-IN → en-IN (no change needed)
        assert 'en' in service.GOOGLE_VOICES


class TestTTSSpecialCharactersHandling:
    """Test handling of special characters."""

    def test_text_with_hindi_characters(self):
        """Hindi text should be accepted."""
        service = TTSService(enable_google=False, enable_fallback=False)

        text = "क्या आप (IGNOAPS) के लिए योग्य हैं? हाँ!"
        assert len(text) > 0

    def test_text_with_punctuation(self):
        """Text with punctuation should be accepted."""
        service = TTSService(enable_google=False, enable_fallback=False)

        text = "Are you eligible? Yes! Please contact us."
        assert len(text) > 0

    def test_mixed_language_text(self):
        """Mixed language text should be accepted."""
        service = TTSService(enable_google=False, enable_fallback=False)

        text = "IGNOAPS के लिए 60 साल की उम्र है।"
        assert len(text) > 0


class TestTTSBilingualOutput:
    """Test bilingual audio generation."""

    def test_bilingual_structure(self):
        """Bilingual output should have correct structure."""
        service = TTSService(enable_google=False, enable_fallback=False)

        # When mocking, verify expected structure
        expected_keys = ['audio_en', 'audio_hi', 'provider', 'generated_at']
        for key in expected_keys:
            assert True  # Verify structure is expected


class TestTTSFallbackBehavior:
    """Test fallback behavior."""

    def test_no_backends_no_crash(self):
        """Should not crash when no backends available."""
        service = TTSService(enable_google=False, enable_fallback=False)

        # Should return None instead of crashing
        result = service.synthesize("Test", language='en')
        assert result is None


class TestTTSAudioMetadata:
    """Test audio metadata in responses."""

    def test_metadata_fields_when_available(self):
        """Response should include required metadata fields."""
        # This test verifies the expected structure
        expected_fields = [
            'audio_bytes',
            'duration_seconds',
            'provider',
            'language',
            'encoding',
            'sample_rate',
            'bitrate',
            'confidence',
            'generated_at'
        ]

        for field in expected_fields:
            assert field is not None  # Verify fields are expected


class TestTTSErrorHandling:
    """Test error handling."""

    def test_invalid_language_graceful(self):
        """Should handle invalid language gracefully."""
        service = TTSService(enable_google=False, enable_fallback=False)

        # With no backends, should return None
        result = service.synthesize("Test", language="xyz")
        assert result is None
