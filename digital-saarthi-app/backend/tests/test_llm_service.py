"""
Tests for LLM Explanation Service

Tests language detection, intent classification, and scheme matching.
"""

import pytest
import sys
from unittest.mock import patch, MagicMock

# Mock OpenAI before importing LLMExplainer
sys.modules['openai'] = MagicMock()

from app.llm_service import LLMExplainer


class TestLLMExplainerInitialization:
    """Test LLM explainer initialization."""

    def test_init_without_openai(self):
        """Should handle missing OpenAI gracefully."""
        with patch('app.llm_service.openai', None):
            explainer = LLMExplainer()
            assert explainer.enabled is False

    def test_init_without_api_key(self):
        """Should warn without API key."""
        with patch.dict('os.environ', {}, clear=True):
            explainer = LLMExplainer(api_key=None)
            # May be disabled if no API key
            assert explainer is not None

    def test_init_with_api_key(self):
        """Should initialize with API key."""
        with patch('app.llm_service.openai') as mock_openai:
            explainer = LLMExplainer(api_key="test-key", model="gpt-3.5-turbo")
            assert explainer.model == "gpt-3.5-turbo"
            assert explainer.temperature == 0.3
            assert explainer.max_tokens == 200


class TestHallucinationDetection:
    """Test hallucination prevention."""

    def test_detect_rupee_amounts(self):
        """Should detect invented rupee amounts."""
        explainer = LLMExplainer(api_key="test-key")

        text = "आप ₹5000 प्रति माह पेंशन पाएंगे।"
        assert explainer._detect_hallucination(text) is True

    def test_detect_rupees_word(self):
        """Should detect 'rupees' with numbers."""
        explainer = LLMExplainer(api_key="test-key")

        text = "You will get rupees 5000 monthly."
        assert explainer._detect_hallucination(text) is True

    def test_detect_monthly_benefit(self):
        """Should detect 'monthly benefit' pattern."""
        explainer = LLMExplainer(api_key="test-key")

        text = "The monthly benefit is substantial."
        assert explainer._detect_hallucination(text) is True

    def test_detect_additional_benefit(self):
        """Should detect 'additional benefit' pattern."""
        explainer = LLMExplainer(api_key="test-key")

        text = "You may also receive additional benefits."
        assert explainer._detect_hallucination(text) is True

    def test_detect_might_also_eligible(self):
        """Should detect speculation about other schemes."""
        explainer = LLMExplainer(api_key="test-key")

        text = "You might also be eligible for PM-Kisan."
        assert explainer._detect_hallucination(text) is True

    def test_no_hallucination_simple_explanation(self):
        """Simple explanation should not be flagged."""
        explainer = LLMExplainer(api_key="test-key")

        text = "आपकी उम्र 65 साल है। इसलिए आप IGNOAPS के लिए योग्य हैं।"
        assert explainer._detect_hallucination(text) is False


class TestDecisionValidation:
    """Test explanation consistency with rule engine."""

    def test_validate_eligible_explanation_true(self):
        """Explanation for eligible=true should not say 'not eligible'."""
        explainer = LLMExplainer(api_key="test-key")

        text = "आप योग्य हैं।"
        assert explainer._validate_against_decision(text, eligible=True) is True

    def test_validate_eligible_explanation_contradiction(self):
        """Explanation contradicting eligible=true should fail."""
        explainer = LLMExplainer(api_key="test-key")

        text = "You are not eligible."
        assert explainer._validate_against_decision(text, eligible=True) is False

    def test_validate_ineligible_explanation_false(self):
        """Explanation for eligible=false should say so."""
        explainer = LLMExplainer(api_key="test-key")

        text = "आपकी उम्र 55 साल है। IGNOAPS के लिए आप योग्य नहीं हैं।"
        assert explainer._validate_against_decision(text, eligible=False) is True

    def test_validate_ineligible_explanation_contradiction(self):
        """Explanation contradicting eligible=false should fail."""
        explainer = LLMExplainer(api_key="test-key")

        text = "You are eligible."
        assert explainer._validate_against_decision(text, eligible=False) is False


class TestExplainEligibility:
    """Test main explanation method."""

    def test_explain_eligible_uses_fallback_when_openai_unavailable(self):
        """Should use fallback when OpenAI unavailable."""
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
        assert "योग्य" in explanation

    def test_explain_ineligible_uses_fallback(self):
        """Should use fallback for ineligible result."""
        explainer = LLMExplainer(api_key="test-key")
        explainer.enabled = False

        result = {
            'eligible': False,
            'scheme': 'IGNOAPS',
            'age': 55,
            'has_bpl': False,
            'reason': 'Age < 60',
            'missing_data': []
        }

        explanation = explainer.explain_eligibility(result, language='en')
        assert explanation
        assert "not" in explanation.lower()

    def test_explain_cannot_determine_uses_fallback(self):
        """Should handle cannot_determine case with fallback."""
        explainer = LLMExplainer(api_key="test-key")
        explainer.enabled = False

        result = {
            'eligible': False,
            'scheme': 'IGNOAPS',
            'age': None,
            'has_bpl': None,
            'reason': 'Missing data',
            'missing_data': ['age', 'bpl_status']
        }

        explanation = explainer.explain_eligibility(result, language='en')
        assert explanation  # Non-empty


class TestExplainMissingData:
    """Test missing data explanation."""

    def test_explain_missing_age_hindi(self):
        """Should ask for missing age in Hindi."""
        explainer = LLMExplainer(api_key="test-key")

        explanation = explainer.explain_missing_data(['age'], language='hi')
        assert "उम्र" in explanation

    def test_explain_missing_bpl_hindi(self):
        """Should ask for missing BPL in Hindi."""
        explainer = LLMExplainer(api_key="test-key")

        explanation = explainer.explain_missing_data(['bpl_status'], language='hi')
        assert "BPL" in explanation

    def test_explain_missing_age_english(self):
        """Should ask for missing age in English."""
        explainer = LLMExplainer(api_key="test-key")

        explanation = explainer.explain_missing_data(['age'], language='en')
        assert "age" in explanation.lower()

    def test_explain_multiple_missing_fields_hindi(self):
        """Should handle multiple missing fields in Hindi."""
        explainer = LLMExplainer(api_key="test-key")

        explanation = explainer.explain_missing_data(
            ['age', 'bpl_status', 'gender'],
            language='hi'
        )
        assert explanation
        assert len(explanation) > 0

    def test_explain_multiple_missing_fields_english(self):
        """Should handle multiple missing fields in English."""
        explainer = LLMExplainer(api_key="test-key")

        explanation = explainer.explain_missing_data(
            ['age', 'bpl_status'],
            language='en'
        )
        assert explanation
        assert "age" in explanation.lower() or "bpl" in explanation.lower()

    def test_explain_no_missing_fields(self):
        """Should return empty string if no missing fields."""
        explainer = LLMExplainer(api_key="test-key")

        explanation = explainer.explain_missing_data([], language='hi')
        assert explanation == ""


class TestExplainActionPlan:
    """Test action plan explanation."""

    def test_explain_action_plan_hindi(self):
        """Should convert action plan to narrative."""
        explainer = LLMExplainer(api_key="test-key")

        action_plan = [
            {'order': 1, 'text_en': 'Visit office', 'text_hi': 'कार्यालय जाएं'},
            {'order': 2, 'text_en': 'Submit documents', 'text_hi': 'दस्तावेज जमा करें'},
        ]

        explanation = explainer.explain_action_plan(action_plan, language='hi')
        assert "कार्यालय" in explanation
        assert "दस्तावेज" in explanation
        assert "1" in explanation

    def test_explain_action_plan_english(self):
        """Should convert action plan to narrative in English."""
        explainer = LLMExplainer(api_key="test-key")

        action_plan = [
            {'order': 1, 'text_en': 'Visit office', 'text_hi': 'कार्यालय जाएं'},
            {'order': 2, 'text_en': 'Submit documents', 'text_hi': 'दस्तावेज जमा करें'},
        ]

        explanation = explainer.explain_action_plan(action_plan, language='en')
        assert "Visit office" in explanation or "visit" in explanation.lower()
        assert "Submit" in explanation or "submit" in explanation.lower()

    def test_explain_empty_action_plan(self):
        """Should handle empty action plan."""
        explainer = LLMExplainer(api_key="test-key")

        explanation = explainer.explain_action_plan([], language='hi')
        assert explanation == ""


class TestFallbackExplanations:
    """Test fallback explanation generation."""

    def test_fallback_eligible_hindi(self):
        """Should provide fallback for eligible=true in Hindi."""
        explainer = LLMExplainer(api_key="test-key")

        fallback = explainer._get_fallback_explanation(eligible=True, language='hi')
        assert fallback
        assert "योग्य" in fallback

    def test_fallback_ineligible_hindi(self):
        """Should provide fallback for eligible=false in Hindi."""
        explainer = LLMExplainer(api_key="test-key")

        fallback = explainer._get_fallback_explanation(eligible=False, language='hi')
        assert fallback
        assert "नहीं" in fallback or "योग्य" in fallback

    def test_fallback_cannot_determine_hindi(self):
        """Should provide fallback for None in Hindi."""
        explainer = LLMExplainer(api_key="test-key")

        fallback = explainer._get_fallback_explanation(eligible=None, language='hi')
        assert fallback
        assert "अधूरी" in fallback or "विवरण" in fallback

    def test_fallback_eligible_english(self):
        """Should provide fallback for eligible=true in English."""
        explainer = LLMExplainer(api_key="test-key")

        fallback = explainer._get_fallback_explanation(eligible=True, language='en')
        assert fallback
        assert "eligible" in fallback.lower()

    def test_fallback_ineligible_english(self):
        """Should provide fallback for eligible=false in English."""
        explainer = LLMExplainer(api_key="test-key")

        fallback = explainer._get_fallback_explanation(eligible=False, language='en')
        assert fallback
        assert "not" in fallback.lower()

    def test_fallback_cannot_determine_english(self):
        """Should provide fallback for None in English."""
        explainer = LLMExplainer(api_key="test-key")

        fallback = explainer._get_fallback_explanation(eligible=None, language='en')
        assert fallback
        assert "incomplete" in fallback.lower()


class TestPromptEngineering:
    """Test prompt safety and structure."""

    def test_system_prompt_hindi_forbids_hallucination(self):
        """System prompt should forbid inventing facts."""
        assert "CANNOT invent" in LLMExplainer.SYSTEM_PROMPT_HI or \
               "आविष्कार" in LLMExplainer.SYSTEM_PROMPT_HI

    def test_system_prompt_english_forbids_hallucination(self):
        """System prompt should forbid inventing facts."""
        assert "CANNOT invent" in LLMExplainer.SYSTEM_PROMPT_EN

    def test_system_prompt_includes_examples(self):
        """System prompts should include examples."""
        assert "Example" in LLMExplainer.SYSTEM_PROMPT_EN or \
               "example" in LLMExplainer.SYSTEM_PROMPT_EN.lower()
