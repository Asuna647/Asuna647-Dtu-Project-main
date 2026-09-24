"""
Stage 7: Error Handler Service

Provides graceful error handling for all system components.
Never crashes; always provides recovery path.
"""

import logging
import hashlib
from typing import Optional, Dict, Any, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class ErrorHandler:
    """Handle errors gracefully without PII exposure."""

    @staticmethod
    def hash_value(value: str) -> str:
        """Hash sensitive values for logging."""
        return hashlib.md5(value.encode()).hexdigest()[:8]

    @staticmethod
    def handle_stt_error(error: Exception) -> Dict[str, Any]:
        """STT failure → ask user to type."""
        logger.warning(f"STT failed: {type(error).__name__}")
        return {
            "status": "degraded",
            "message": "Audio transcription failed. Please type your question instead.",
            "recovery_path": "manual_input",
            "user_action": "Enter text instead of voice"
        }

    @staticmethod
    def handle_ocr_error(error: Exception) -> Dict[str, Any]:
        """OCR failure → ask user to enter manually."""
        logger.warning(f"OCR failed: {type(error).__name__}")
        return {
            "status": "degraded",
            "message": "Document reading failed. Please enter your details manually.",
            "recovery_path": "manual_entry",
            "fields_needed": ["age", "bpl_status"],
            "user_action": "Fill the form with your information"
        }

    @staticmethod
    def handle_rules_error(error: Exception) -> Dict[str, Any]:
        """Rules engine failure → cannot_determine (never guess)."""
        logger.error(f"Rules engine failed: {type(error).__name__}")
        return {
            "eligible": False,
            "verdict": "cannot_determine",
            "confidence": 0.0,
            "reason": "System unable to determine eligibility. Please try again.",
            "user_action": "Contact support"
        }

    @staticmethod
    def handle_llm_error(error: Exception, fallback: str) -> str:
        """LLM failure → use fallback explanation."""
        logger.warning(f"LLM failed: {type(error).__name__}. Using fallback.")
        return fallback

    @staticmethod
    def handle_tts_error(error: Exception) -> None:
        """TTS failure → return text only (no crash)."""
        logger.warning(f"TTS failed: {type(error).__name__}. Continuing without audio.")
        return None

    @staticmethod
    def log_error(error: Exception, context: Dict[str, Any], pii_safe: bool = True):
        """Log error without exposing PII."""
        safe_context = {k: v for k, v in context.items()
                       if k not in ['query', 'audio', 'document', 'user_data']}
        logger.error(
            f"{type(error).__name__}: {str(error)[:100]}. Context: {safe_context}",
            exc_info=False
        )
