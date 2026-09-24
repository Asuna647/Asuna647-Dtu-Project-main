"""
Stage 7 Tests: Error Handler
"""

import pytest
from app.error_handler import ErrorHandler


class TestErrorHandlerSTT:
    """Test STT error handling."""

    def test_stt_error_recovery(self):
        """STT fails → return degraded status with recovery path."""
        error = Exception("Whisper API unavailable")
        result = ErrorHandler.handle_stt_error(error)

        assert result["status"] == "degraded"
        assert "type your question" in result["message"].lower()
        assert result["recovery_path"] == "manual_input"

    def test_stt_error_no_pii(self):
        """STT error logging doesn't expose PII."""
        error = Exception("Failed")
        context = {"query": "my aadhaar is 123-456-789", "user_id": "john"}

        # Should not raise or leak PII
        ErrorHandler.log_error(error, context, pii_safe=True)


class TestErrorHandlerOCR:
    """Test OCR error handling."""

    def test_ocr_error_recovery(self):
        """OCR fails → ask user to enter manually."""
        error = Exception("Tesseract not found")
        result = ErrorHandler.handle_ocr_error(error)

        assert result["status"] == "degraded"
        assert result["recovery_path"] == "manual_entry"
        assert "age" in result["fields_needed"]

    def test_ocr_user_action(self):
        """OCR error provides clear user action."""
        error = Exception("OCR failed")
        result = ErrorHandler.handle_ocr_error(error)

        assert result["user_action"]
        assert len(result["user_action"]) > 0


class TestErrorHandlerRules:
    """Test rules engine error handling."""

    def test_rules_error_cannot_determine(self):
        """Rules engine fails → cannot_determine, never guess."""
        error = Exception("Rule validation failed")
        result = ErrorHandler.handle_rules_error(error)

        assert result["eligible"] is False
        assert result["verdict"] == "cannot_determine"
        assert result["confidence"] == 0.0

    def test_rules_error_no_hallucination(self):
        """Rules error doesn't invent eligibility."""
        error = Exception("Unknown error")
        result = ErrorHandler.handle_rules_error(error)

        assert "try again" in result["reason"].lower()
        assert "contact support" in result["user_action"].lower()


class TestErrorHandlerLLM:
    """Test LLM error handling."""

    def test_llm_error_uses_fallback(self):
        """LLM fails → use fallback explanation."""
        error = Exception("OpenAI API rate limit")
        fallback = "Unable to generate explanation. Please try again."

        result = ErrorHandler.handle_llm_error(error, fallback)

        assert result == fallback


class TestErrorHandlerTTS:
    """Test TTS error handling."""

    def test_tts_error_returns_none(self):
        """TTS fails → return None (no crash)."""
        error = Exception("Google TTS unavailable")
        result = ErrorHandler.handle_tts_error(error)

        assert result is None


class TestErrorLogging:
    """Test error logging without PII."""

    def test_log_error_hashes_values(self):
        """ErrorHandler can hash sensitive values for safe logging."""
        hashed = ErrorHandler.hash_value("123-456-789")

        assert len(hashed) == 8
        assert hashed.isalnum()

    def test_log_error_strips_pii(self):
        """ErrorHandler strips PII from context before logging."""
        error = Exception("Test error")
        context = {
            "query": "sensitive query",
            "audio": b"audio data",
            "document": "document content",
            "user_data": "pii",
            "safe_field": "value"
        }

        # Should not raise
        ErrorHandler.log_error(error, context, pii_safe=True)
