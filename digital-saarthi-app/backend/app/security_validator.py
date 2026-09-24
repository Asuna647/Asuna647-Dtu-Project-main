"""
Stage 7: Security Validator

Input validation, rate limiting, and security hardening.
"""

import re
from typing import Tuple, Dict, Any
from datetime import datetime, timedelta
from collections import defaultdict

class SecurityValidator:
    """Validate all inputs before processing."""

    # Rate limit tracking (IP -> request history)
    _rate_limits: Dict[str, list] = defaultdict(list)

    ALLOWED_AUDIO_MIMES = {"audio/wav", "audio/mpeg", "audio/mp3", "audio/m4a", "audio/flac"}
    ALLOWED_DOC_MIMES = {"image/jpeg", "image/png", "application/pdf"}

    MAX_AUDIO_SIZE_MB = 10
    MAX_DOC_SIZE_MB = 50
    MAX_REQUEST_SIZE_MB = 100

    @staticmethod
    def validate_audio_file(filename: str, mime_type: str, file_size: int) -> Tuple[bool, str]:
        """Validate audio file upload."""
        # Check MIME type
        if mime_type not in SecurityValidator.ALLOWED_AUDIO_MIMES:
            return (False, f"Invalid audio format. Allowed: WAV, MP3, M4A, FLAC")

        # Check file size
        size_mb = file_size / (1024 * 1024)
        if size_mb > SecurityValidator.MAX_AUDIO_SIZE_MB:
            return (False, f"Audio file exceeds {SecurityValidator.MAX_AUDIO_SIZE_MB} MB limit")

        # Check filename (no path traversal)
        if "/" in filename or "\\" in filename or ".." in filename:
            return (False, "Invalid filename")

        return (True, "Valid audio file")

    @staticmethod
    def validate_document_upload(filename: str, mime_type: str, file_size: int) -> Tuple[bool, str]:
        """Validate document upload."""
        # Check MIME type
        if mime_type not in SecurityValidator.ALLOWED_DOC_MIMES:
            return (False, f"Invalid document format. Allowed: JPEG, PNG, PDF")

        # Check file size
        size_mb = file_size / (1024 * 1024)
        if size_mb > SecurityValidator.MAX_DOC_SIZE_MB:
            return (False, f"Document exceeds {SecurityValidator.MAX_DOC_SIZE_MB} MB limit")

        # Check filename
        if "/" in filename or "\\" in filename or ".." in filename:
            return (False, "Invalid filename")

        return (True, "Valid document")

    @staticmethod
    def validate_form_input(data: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate form data."""
        # Age validation
        if "age" in data:
            try:
                age = int(data["age"])
                if age < 0 or age > 120:
                    return (False, "Age must be between 0 and 120")
            except (ValueError, TypeError):
                return (False, "Age must be a number")

        # BPL validation
        if "bpl_status" in data:
            if not isinstance(data["bpl_status"], bool):
                return (False, "BPL status must be true or false")

        # Gender validation
        if "gender" in data:
            if data["gender"] not in ["male", "female", "other"]:
                return (False, "Gender must be male, female, or other")

        return (True, "Valid form input")

    @staticmethod
    def sanitize_query_text(text: str) -> str:
        """Remove dangerous characters from text input."""
        # Remove control characters
        text = ''.join(ch for ch in text if ord(ch) >= 32 or ch in '\n\t')

        # Reduce multiple spaces
        text = re.sub(r'\s+', ' ', text).strip()

        return text[:1000]  # Max 1000 characters

    @staticmethod
    def rate_limit_check(client_ip: str, limit_per_minute: int = 100) -> Tuple[bool, str]:
        """Check rate limits."""
        now = datetime.utcnow()
        minute_ago = now - timedelta(minutes=1)

        # Clean old entries
        if client_ip in SecurityValidator._rate_limits:
            SecurityValidator._rate_limits[client_ip] = [
                ts for ts in SecurityValidator._rate_limits[client_ip]
                if ts > minute_ago
            ]

        # Check limit
        if len(SecurityValidator._rate_limits[client_ip]) >= limit_per_minute:
            return (False, "Rate limit exceeded. Please try again later.")

        # Record request
        SecurityValidator._rate_limits[client_ip].append(now)

        return (True, "Request allowed")

    @staticmethod
    def check_request_size(content_length: int) -> Tuple[bool, str]:
        """Check request body size."""
        size_mb = content_length / (1024 * 1024)
        if size_mb > SecurityValidator.MAX_REQUEST_SIZE_MB:
            return (False, f"Request exceeds {SecurityValidator.MAX_REQUEST_SIZE_MB} MB limit")
        return (True, "Request size OK")

    @staticmethod
    def validate_audio_duration(duration_seconds: float) -> Tuple[bool, str]:
        """Validate audio duration."""
        if duration_seconds < 0.5:
            return (False, "Audio too short (< 0.5 seconds)")
        if duration_seconds > 300:  # 5 minutes
            return (False, "Audio too long (> 5 minutes)")
        return (True, "Audio duration OK")
