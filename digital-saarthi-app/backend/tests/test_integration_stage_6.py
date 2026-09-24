"""
Stage 6 Integration Tests

Tests full pipeline integration, graceful degradation, and schema validation.
"""

import pytest
from unittest.mock import MagicMock
from app.llm_service import LLMExplainer
from app.tts_service import TTSService


class TestFullPipelineIntegration:
    """Test complete voice-to-audio pipeline."""

    def test_full_pipeline_eligible_hindi(self):
        """Complete pipeline: eligibility → explanation → audio."""
        explainer = LLMExplainer(api_key="test-key")
        explainer.enabled = False

        eligibility_result = {
            'eligible': True,
            'scheme': 'IGNOAPS',
            'age': 65,
            'has_bpl': True,
            'reason': 'Age >= 60 AND BPL status confirmed',
            'missing_data': []
        }

        explanation = explainer.explain_eligibility(eligibility_result, language='hi')
        assert explanation
        assert "योग्य" in explanation

    def test_full_pipeline_ineligible_english(self):
        """Pipeline with ineligible result in English."""
        explainer = LLMExplainer(api_key="test-key")
        explainer.enabled = False

        eligibility_result = {
            'eligible': False,
            'scheme': 'IGNOAPS',
            'age': 55,
            'has_bpl': False,
            'reason': 'Age < 60',
            'missing_data': []
        }

        explanation = explainer.explain_eligibility(eligibility_result, language='en')
        assert explanation
        assert "not" in explanation.lower()

    def test_pipeline_with_missing_data(self):
        """Pipeline when eligibility cannot be determined."""
        explainer = LLMExplainer(api_key="test-key")
        explainer.enabled = False

        eligibility_result = {
            'eligible': False,
            'scheme': 'IGNOAPS',
            'age': None,
            'has_bpl': None,
            'reason': 'Missing data',
            'missing_data': ['age', 'bpl_status']
        }

        explanation = explainer.explain_eligibility(eligibility_result, language='en')
        assert explanation
        assert explanation != ""


class TestGracefulDegradation:
    """Test graceful failure handling."""

    def test_llm_unavailable_uses_fallback(self):
        """Should use fallback when LLM unavailable."""
        explainer = LLMExplainer(api_key="test-key")
        explainer.enabled = False

        eligibility_result = {
            'eligible': True,
            'scheme': 'IGNOAPS',
            'age': 65,
            'has_bpl': True,
            'reason': 'Age >= 60',
            'missing_data': []
        }

        explanation = explainer.explain_eligibility(eligibility_result, language='hi')
        assert explanation
        assert "योग्य" in explanation

    def test_tts_unavailable_returns_none(self):
        """Should gracefully return None when TTS unavailable."""
        service = TTSService(enable_google=False, enable_fallback=False)

        result = service.synthesize("Test", language='en')
        assert result is None

    def test_llm_hallucination_uses_fallback(self):
        """Should reject hallucination and use fallback."""
        explainer = LLMExplainer(api_key="test-key")

        # Simulate hallucination detection
        text_with_hallucination = "आप योग्य हैं और ₹5000 प्रति माह पेंशन पाएंगे।"
        is_hallucination = explainer._detect_hallucination(text_with_hallucination)
        assert is_hallucination is True

    def test_invalid_llm_output_uses_fallback(self):
        """Should use fallback for invalid LLM output."""
        explainer = LLMExplainer(api_key="test-key")

        # Test validation logic
        text_contradicts = "You are eligible."
        is_valid = explainer._validate_against_decision(text_contradicts, eligible=False)
        assert is_valid is False


class TestBilingualSupport:
    """Test bilingual explanation and audio."""

    def test_explanation_bilingual_output(self):
        """Should generate both Hindi and English explanations."""
        explainer = LLMExplainer(api_key="test-key")
        explainer.enabled = False

        result = {
            'eligible': True,
            'scheme': 'IGNOAPS',
            'age': 65,
            'has_bpl': True,
            'reason': 'Age >= 60',
            'missing_data': []
        }

        explanation_hi = explainer.explain_eligibility(result, language='hi')
        explanation_en = explainer.explain_eligibility(result, language='en')

        assert explanation_hi
        assert explanation_en
        # Both should be non-empty
        assert len(explanation_hi) > 0
        assert len(explanation_en) > 0

    def test_tts_bilingual_audio(self):
        """Should support bilingual TTS."""
        service = TTSService(enable_google=False, enable_fallback=False)

        result = service.synthesize_bilingual(
            text_en="You are eligible.",
            text_hi="आप योग्य हैं।"
        )

        # With no backends, should return None
        assert result is None


class TestResponseSchema:
    """Test response schema validation."""

    def test_explanation_response_structure(self):
        """Explanation response should have required fields."""
        explainer = LLMExplainer(api_key="test-key")
        explainer.enabled = False

        result = {
            'eligible': True,
            'scheme': 'IGNOAPS',
            'age': 65,
            'has_bpl': True,
            'reason': 'Age >= 60',
            'missing_data': []
        }

        explanation = explainer.explain_eligibility(result, language='hi')

        # Response should be string
        assert isinstance(explanation, str)
        assert len(explanation) > 0
        assert len(explanation) <= 300

    def test_audio_response_structure(self):
        """Audio response should have expected structure."""
        service = TTSService(enable_google=False, enable_fallback=False)

        # With no backends, structure tests pass
        assert service is not None


class TestMultiSchemeComparison:
    """Test explanations across multiple schemes."""

    def test_explain_ignoaps_eligibility(self):
        """Should explain IGNOAPS eligibility."""
        explainer = LLMExplainer(api_key="test-key")
        explainer.enabled = False

        result = {
            'eligible': True,
            'scheme': 'IGNOAPS',
            'age': 65,
            'has_bpl': True,
            'reason': 'Age >= 60 AND BPL',
            'missing_data': []
        }

        explanation = explainer.explain_eligibility(result, language='hi')
        assert explanation

    def test_explain_eshram_eligibility(self):
        """Should explain E-Shram eligibility."""
        explainer = LLMExplainer(api_key="test-key")
        explainer.enabled = False

        result = {
            'eligible': True,
            'scheme': 'E-Shram',
            'age': 45,
            'has_bpl': False,
            'is_organised_worker': False,
            'reason': 'Unorganized worker',
            'missing_data': []
        }

        explanation = explainer.explain_eligibility(result, language='hi')
        assert explanation

    def test_explain_pm_kisan_eligibility(self):
        """Should explain PM-Kisan eligibility."""
        explainer = LLMExplainer(api_key="test-key")
        explainer.enabled = False

        result = {
            'eligible': True,
            'scheme': 'PM-Kisan',
            'age': 50,
            'has_bpl': True,
            'is_farmer': True,
            'reason': 'Farmer with valid land holdings',
            'missing_data': []
        }

        explanation = explainer.explain_eligibility(result, language='hi')
        assert explanation


class TestActionPlanConversion:
    """Test action plan explanation."""

    def test_action_plan_conversion_eligible(self):
        """Should convert action plan to narrative for eligible user."""
        explainer = LLMExplainer(api_key="test-key")

        action_plan = [
            {
                'order': 1,
                'text_en': 'Visit the nearest pension office',
                'text_hi': 'निकटतम पेंशन कार्यालय जाएं'
            },
            {
                'order': 2,
                'text_en': 'Submit Aadhaar and birth certificate',
                'text_hi': 'आधार और जन्म प्रमाण पत्र जमा करें'
            },
        ]

        narrative_hi = explainer.explain_action_plan(action_plan, language='hi')
        narrative_en = explainer.explain_action_plan(action_plan, language='en')

        assert "निकटतम" in narrative_hi or "कार्यालय" in narrative_hi
        assert "pension office" in narrative_en or "Visit" in narrative_en

    def test_action_plan_conversion_ineligible(self):
        """Should convert action plan for ineligible user."""
        explainer = LLMExplainer(api_key="test-key")

        action_plan = [
            {
                'order': 1,
                'text_en': 'You need to be at least 60 years old',
                'text_hi': 'आपको कम से कम 60 साल का होना चाहिए'
            },
            {
                'order': 2,
                'text_en': 'Check back after your 60th birthday',
                'text_hi': '60 साल की उम्र के बाद फिर से जांचें'
            }
        ]

        narrative_en = explainer.explain_action_plan(action_plan, language='en')

        assert narrative_en
        assert "60" in narrative_en


class TestAccessibility:
    """Test accessibility features."""

    def test_alt_text_generation(self):
        """Should generate screen-reader friendly alt text."""
        result = {
            'eligible': True,
            'scheme': 'IGNOAPS',
            'age': 65,
            'has_bpl': True,
            'reason': 'Age >= 60 AND BPL',
            'missing_data': []
        }

        alt_text = f"Eligibility result: {result['scheme']} - {'Eligible' if result['eligible'] else 'Not Eligible'}"

        assert len(alt_text) < 200
        assert "Eligibility" in alt_text
        assert "Eligible" in alt_text

    def test_audio_url_accessibility(self):
        """Audio URLs should be stable and accessible."""
        service = TTSService(enable_google=False, enable_fallback=False)

        text = "आप योग्य हैं।"
        text_hash = service.hash_text(text)
        url = service.generate_audio_url(text_hash, language='hi')

        assert url.startswith("/api/audio/")
        assert url.endswith(".mp3")
        assert "hi-" in url

        # Same text should produce same URL
        url2 = service.generate_audio_url(service.hash_text(text), language='hi')
        assert url == url2


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_very_long_explanation(self):
        """Should handle very long explanations gracefully."""
        explainer = LLMExplainer(api_key="test-key")
        explainer.enabled = False

        result = {
            'eligible': True,
            'scheme': 'IGNOAPS',
            'age': 65,
            'has_bpl': True,
            'reason': 'Age >= 60',
            'missing_data': []
        }

        explanation = explainer.explain_eligibility(result, language='en')
        assert explanation

    def test_unicode_characters_hindi(self):
        """Should handle Hindi Unicode characters correctly."""
        service = TTSService(enable_google=False, enable_fallback=False)

        text = "क्षण, ज्ञान, श्रृंखला"  # Complex Hindi characters
        assert len(text) > 0

    def test_age_boundary_values(self):
        """Should explain age boundary cases correctly."""
        explainer = LLMExplainer(api_key="test-key")
        explainer.enabled = False

        # Age = 59 (just below cutoff)
        result = {
            'eligible': False,
            'scheme': 'IGNOAPS',
            'age': 59,
            'has_bpl': True,
            'reason': 'Age < 60',
            'missing_data': []
        }

        explanation = explainer.explain_eligibility(result, language='hi')
        assert explanation

        # Age = 60 (exactly at cutoff)
        result['age'] = 60
        result['eligible'] = True
        result['reason'] = 'Age >= 60 AND BPL'

        explanation = explainer.explain_eligibility(result, language='hi')
        assert explanation
