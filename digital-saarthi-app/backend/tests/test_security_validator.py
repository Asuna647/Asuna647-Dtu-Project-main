"""
Stage 7 Tests: Security Validator
"""

import pytest
from app.security_validator import SecurityValidator


class TestAudioFileValidation:
    """Test audio file upload validation."""

    def test_valid_audio_wav(self):
        """Valid WAV file passes validation."""
        valid, msg = SecurityValidator.validate_audio_file(
            "audio.wav", "audio/wav", 5 * 1024 * 1024
        )
        assert valid is True

    def test_valid_audio_mp3(self):
        """Valid MP3 file passes validation."""
        valid, msg = SecurityValidator.validate_audio_file(
            "audio.mp3", "audio/mpeg", 8 * 1024 * 1024
        )
        assert valid is True

    def test_invalid_audio_format(self):
        """Invalid audio format rejected."""
        valid, msg = SecurityValidator.validate_audio_file(
            "audio.exe", "application/x-msdownload", 1 * 1024 * 1024
        )
        assert valid is False
        assert "Invalid audio format" in msg

    def test_audio_size_exceeded(self):
        """Audio file exceeding 10MB rejected."""
        valid, msg = SecurityValidator.validate_audio_file(
            "audio.wav", "audio/wav", 15 * 1024 * 1024
        )
        assert valid is False
        assert "exceeds" in msg

    def test_audio_path_traversal(self):
        """Path traversal in filename rejected."""
        valid, msg = SecurityValidator.validate_audio_file(
            "../../../etc/passwd", "audio/wav", 1 * 1024 * 1024
        )
        assert valid is False


class TestDocumentValidation:
    """Test document upload validation."""

    def test_valid_document_jpeg(self):
        """Valid JPEG document passes validation."""
        valid, msg = SecurityValidator.validate_document_upload(
            "document.jpg", "image/jpeg", 30 * 1024 * 1024
        )
        assert valid is True

    def test_valid_document_png(self):
        """Valid PNG document passes validation."""
        valid, msg = SecurityValidator.validate_document_upload(
            "document.png", "image/png", 20 * 1024 * 1024
        )
        assert valid is True

    def test_invalid_document_format(self):
        """Invalid document format rejected."""
        valid, msg = SecurityValidator.validate_document_upload(
            "document.txt", "text/plain", 1 * 1024 * 1024
        )
        assert valid is False

    def test_document_size_exceeded(self):
        """Document exceeding 50MB rejected."""
        valid, msg = SecurityValidator.validate_document_upload(
            "document.pdf", "application/pdf", 60 * 1024 * 1024
        )
        assert valid is False


class TestFormInputValidation:
    """Test form data validation."""

    def test_valid_age(self):
        """Valid age passes validation."""
        valid, msg = SecurityValidator.validate_form_input({"age": 65})
        assert valid is True

    def test_invalid_age_negative(self):
        """Negative age rejected."""
        valid, msg = SecurityValidator.validate_form_input({"age": -5})
        assert valid is False

    def test_invalid_age_too_old(self):
        """Age > 120 rejected."""
        valid, msg = SecurityValidator.validate_form_input({"age": 150})
        assert valid is False

    def test_valid_bpl_status(self):
        """Valid BPL status passes."""
        valid, msg = SecurityValidator.validate_form_input({"bpl_status": True})
        assert valid is True

    def test_invalid_bpl_status(self):
        """Non-boolean BPL rejected."""
        valid, msg = SecurityValidator.validate_form_input({"bpl_status": "yes"})
        assert valid is False

    def test_valid_gender(self):
        """Valid gender passes."""
        for gender in ["male", "female", "other"]:
            valid, msg = SecurityValidator.validate_form_input({"gender": gender})
            assert valid is True

    def test_invalid_gender(self):
        """Invalid gender rejected."""
        valid, msg = SecurityValidator.validate_form_input({"gender": "unknown"})
        assert valid is False


class TestTextSanitization:
    """Test query text sanitization."""

    def test_sanitize_removes_control_chars(self):
        """Control characters removed."""
        text = "Hello\x00World\x01Test"
        sanitized = SecurityValidator.sanitize_query_text(text)
        assert "\x00" not in sanitized
        assert "\x01" not in sanitized

    def test_sanitize_normalizes_spaces(self):
        """Multiple spaces normalized."""
        text = "Hello    World    Test"
        sanitized = SecurityValidator.sanitize_query_text(text)
        assert "    " not in sanitized

    def test_sanitize_max_length(self):
        """Text truncated to max 1000 chars."""
        text = "a" * 2000
        sanitized = SecurityValidator.sanitize_query_text(text)
        assert len(sanitized) <= 1000


class TestRateLimiting:
    """Test rate limiting."""

    def test_rate_limit_allows_requests(self):
        """Requests under limit allowed."""
        SecurityValidator._rate_limits.clear()

        for i in range(5):
            allowed, msg = SecurityValidator.rate_limit_check("127.0.0.1", limit_per_minute=100)
            assert allowed is True

    def test_rate_limit_blocks_excess(self):
        """Requests exceeding limit blocked."""
        SecurityValidator._rate_limits.clear()

        # Fill limit
        for i in range(10):
            SecurityValidator.rate_limit_check("127.0.0.1", limit_per_minute=10)

        # Next should be blocked
        allowed, msg = SecurityValidator.rate_limit_check("127.0.0.1", limit_per_minute=10)
        assert allowed is False
        assert "Rate limit exceeded" in msg

    def test_rate_limit_per_ip(self):
        """Rate limits per IP address."""
        SecurityValidator._rate_limits.clear()

        # Fill limit for IP1
        for i in range(5):
            SecurityValidator.rate_limit_check("192.168.1.1", limit_per_minute=5)

        # IP2 should have fresh limit
        allowed, msg = SecurityValidator.rate_limit_check("192.168.1.2", limit_per_minute=5)
        assert allowed is True


class TestRequestSizeValidation:
    """Test request size validation."""

    def test_request_size_under_limit(self):
        """Requests under limit allowed."""
        valid, msg = SecurityValidator.check_request_size(50 * 1024 * 1024)
        assert valid is True

    def test_request_size_exceeds_limit(self):
        """Requests exceeding 100MB rejected."""
        valid, msg = SecurityValidator.check_request_size(150 * 1024 * 1024)
        assert valid is False


class TestAudioDurationValidation:
    """Test audio duration validation."""

    def test_valid_duration(self):
        """Valid duration passes."""
        valid, msg = SecurityValidator.validate_audio_duration(5.0)
        assert valid is True

    def test_duration_too_short(self):
        """Audio < 0.5s rejected."""
        valid, msg = SecurityValidator.validate_audio_duration(0.2)
        assert valid is False

    def test_duration_too_long(self):
        """Audio > 5 minutes rejected."""
        valid, msg = SecurityValidator.validate_audio_duration(350)
        assert valid is False
