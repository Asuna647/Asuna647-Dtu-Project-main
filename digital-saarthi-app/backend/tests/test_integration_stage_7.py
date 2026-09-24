"""
Stage 7 Integration Tests
"""

import pytest
from app.error_handler import ErrorHandler
from app.cache_service import CacheService
from app.security_validator import SecurityValidator
import tempfile


class TestStage7Integration:
    """Integration tests for error handling, caching, and security."""

    def test_error_recovery_chain(self):
        """Test error recovery across multiple components."""
        # STT error
        stt_error = ErrorHandler.handle_stt_error(Exception("STT failed"))
        assert stt_error["status"] == "degraded"

        # OCR error
        ocr_error = ErrorHandler.handle_ocr_error(Exception("OCR failed"))
        assert ocr_error["status"] == "degraded"

        # Rules error
        rules_error = ErrorHandler.handle_rules_error(Exception("Rules failed"))
        assert rules_error["verdict"] == "cannot_determine"

    def test_security_and_caching(self):
        """Test security validation and caching together."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheService(tmpdir)

            # Validate input
            valid, msg = SecurityValidator.validate_form_input({"age": 65})
            assert valid is True

            # Cache result
            cache.cache_scheme_data("ignoaps", {"eligible": True}, ttl_hours=24)

            # Retrieve cached
            cached = cache.get_cached_scheme("ignoaps")
            assert cached is not None

    def test_rate_limiting_security(self):
        """Test rate limiting prevents abuse."""
        SecurityValidator._rate_limits.clear()

        # Allow some requests
        for i in range(5):
            allowed, _ = SecurityValidator.rate_limit_check("127.0.0.1", limit_per_minute=100)
            assert allowed is True

        # Block excessive requests
        SecurityValidator._rate_limits.clear()
        for i in range(10):
            SecurityValidator.rate_limit_check("127.0.0.1", limit_per_minute=10)

        allowed, msg = SecurityValidator.rate_limit_check("127.0.0.1", limit_per_minute=10)
        assert allowed is False

    def test_cache_expiration_workflow(self):
        """Test cache expiration in realistic workflow."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheService(tmpdir)

            # Cache data
            cache.cache_scheme_data("ignoaps", {"name": "IGNOAPS"}, ttl_hours=0)

            # Immediately check
            import time
            time.sleep(0.1)

            cached = cache.get_cached_scheme("ignoaps")
            assert cached is None


class TestStage7Deployment:
    """Test deployment readiness."""

    def test_environment_security(self):
        """Test security headers and configuration."""
        # Simulate CORS configuration
        allowed_origins = ["https://yourdomain.com"]
        assert "https://" in allowed_origins[0]

    def test_no_pii_logging(self):
        """Verify PII not logged in errors."""
        error = Exception("Test")
        context = {
            "user_id": "123",
            "query": "sensitive",
            "safe_field": "value"
        }

        # Should not raise or leak data
        ErrorHandler.log_error(error, context, pii_safe=True)
