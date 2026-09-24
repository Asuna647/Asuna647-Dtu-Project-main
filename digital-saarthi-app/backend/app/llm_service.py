"""
Stage 6: LLM Explanation Service

Provides safe LLM-based explanations of verified eligibility results.

CRITICAL SAFETY PRINCIPLE:
- LLM explains only verified facts from the rule engine
- LLM CANNOT invent eligibility criteria, benefits, or amounts
- LLM receives only typed IntegrationResult objects
- All outputs validated against rule engine decision

Architecture:
RULE ENGINE (decides eligible/ineligible)
    ↓
    ├─ Decision: eligible=true/false
    ├─ Reason: verified rule explanation
    └─ Age, BPL, scheme: typed, validated data
    ↓
LLM EXPLAINER (explains ONLY the decision)
    ├─ Input: structured eligibility result
    ├─ Safety: strict prompt forbids hallucination
    ├─ Output: simple 2-3 sentence explanation
    └─ Validation: checked against rule engine decision
"""

import logging
import re
from typing import Optional, List, Dict, Any
from datetime import datetime
import os

try:
    import openai
except ImportError:
    openai = None

logger = logging.getLogger(__name__)


class LLMExplainer:
    """Safe LLM wrapper for explaining verified eligibility results."""

    # Strict system prompt to prevent hallucination
    SYSTEM_PROMPT_HI = """आप एक सरल सरकारी पेंशन योग्यता व्याख्याकार हैं।

महत्वपूर्ण नियम:
1. आप केवल नियम इंजन द्वारा सत्यापित तथ्यों की व्याख्या कर सकते हैं।
2. आप पात्रता मानदंड, लाभ की राशि, या आवश्यकताओं का आविष्कार नहीं कर सकते।
3. आप अनुमान या अपूर्ण जानकारी नहीं दे सकते।
4. यदि आपके पास सत्यापित जानकारी नहीं है, तो कहें "यह जानकारी उपलब्ध नहीं है।"

आपका भूमिका सत्यापित निर्णयों को सरल और सुलभ बनाना है।

आप पाएंगे:
- योग्य: true/false
- योजना: "IGNOAPS" या अन्य
- उम्र: संख्या
- BPL: true/false
- कारण: क्यों योग्य/अयोग्य है

आउटपुट: 2-3 सरल वाक्य हिंदी में।

उदाहरण:
इनपुट: योग्य=true, योजना="IGNOAPS", उम्र=65, कारण="उम्र >= 60 AND BPL"
आउटपुट: "आपकी उम्र 65 साल है और आप BPL में हैं। इसलिए आप IGNOAPS पेंशन के लिए योग्य हैं।"

इनपुट: योग्य=false, योजना="IGNOAPS", उम्र=55, कारण="उम्र < 60"
आउटपुट: "आपकी उम्र 55 साल है। IGNOAPS के लिए कम से कम 60 साल होना जरूरी है।"

मना किया गया:
- ₹X प्रति माह न कहें (केवल नियम इंजन को पता है)
- "आप X के लिए भी योग्य हो सकते हैं" न कहें (केवल नियम इंजन ने निर्धारित किया)
- "आमतौर पर लोग पाते हैं..." न कहें (केवल सत्यापित नियम)
- परिणाम ऑब्जेक्ट में नहीं है ऐसी जानकारी न जोड़ें"""

    SYSTEM_PROMPT_EN = """You are a simple government pension eligibility explainer.

CRITICAL RULES:
1. You can ONLY explain facts verified by the rule engine.
2. You CANNOT invent eligibility criteria, benefit amounts, or requirements.
3. You CANNOT hallucinate or guess.
4. If you don't have verified information, say "This information is not available."

Your role is to make verified decisions SIMPLE and ACCESSIBLE.

Input you will receive: structured eligibility result with:
- eligible: true/false
- scheme: "IGNOAPS" or other
- age: number
- has_bpl: true/false
- reason: why eligible/ineligible

Output: 2-3 simple sentences in English.

Example:
Input: eligible=true, scheme="IGNOAPS", age=65, reason="Age >= 60 AND BPL"
Output: "Your age is 65 and you have BPL status. Therefore, you are eligible for IGNOAPS pension."

Input: eligible=false, scheme="IGNOAPS", age=55, reason="Age < 60"
Output: "Your age is 55. For IGNOAPS, you must be at least 60 years old."

FORBIDDEN:
- Do NOT say "₹X per month" (only rule engine knows amounts)
- Do NOT say "You might also be eligible for X" (only what rule engine determined)
- Do NOT say "Typically, people get..." (only verified rules)
- Do NOT add information not in the result object"""

    # Hallucination detection patterns
    HALLUCINATION_PATTERNS = [
        r'₹\s*\d+',  # Rupee amounts
        r'rupees?\s+\d+',  # Word rupees with numbers
        r'monthly\s+benefit',  # Monthly benefit (not in rule engine)
        r'additional\s+benefit',  # Additional benefits
        r'special\s+category',  # Special categories not verified
        r'might\s+also\s+be\s+eligible',  # Speculation
        r'typically',  # Generalizations
        r'usually',  # Generalizations
    ]

    FALLBACK_EXPLANATIONS_HI = {
        'eligible_generic': 'आप इस योजना के लिए योग्य हैं।',
        'ineligible_generic': 'आप इस योजना के लिए योग्य नहीं हैं।',
        'cannot_determine': 'आपकी जानकारी अधूरी है। कृपया सभी विवरण प्रदान करें।',
    }

    FALLBACK_EXPLANATIONS_EN = {
        'eligible_generic': 'You are eligible for this scheme.',
        'ineligible_generic': 'You are not eligible for this scheme.',
        'cannot_determine': 'Your information is incomplete. Please provide all details.',
    }

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-3.5-turbo"):
        """
        Initialize LLM explainer with safety guardrails.

        Args:
            api_key: OpenAI API key (env var: OPENAI_API_KEY if not provided)
            model: LLM model to use (default: gpt-3.5-turbo)

        Raises:
            ValueError: If OpenAI not available or no API key
        """
        if openai is None:
            logger.warning("OpenAI not available. LLM explanations will use fallback.")
            self.enabled = False
            return

        api_key = api_key or os.getenv('OPENAI_API_KEY')
        if not api_key:
            logger.warning("No OpenAI API key provided. LLM explanations will use fallback.")
            self.enabled = False
            return

        openai.api_key = api_key
        self.model = model
        self.enabled = True
        self.temperature = 0.3  # Low temperature for deterministic output
        self.max_tokens = 200  # Keep explanations concise

    def _detect_hallucination(self, text: str) -> bool:
        """
        Detect common hallucination patterns in LLM output.

        Args:
            text: LLM output to check

        Returns:
            True if hallucination detected, False otherwise
        """
        text_lower = text.lower()
        for pattern in self.HALLUCINATION_PATTERNS:
            if re.search(pattern, text_lower):
                logger.warning(f"Hallucination detected: pattern '{pattern}' in output")
                return True
        return False

    def _validate_against_decision(self, explanation: str, eligible: bool) -> bool:
        """
        Validate explanation matches the rule engine decision.

        Args:
            explanation: LLM explanation
            eligible: Rule engine eligibility decision

        Returns:
            True if consistent, False if contradicts rule engine
        """
        exp_lower = explanation.lower()

        # Check for contradictions
        if eligible:
            # If eligible, should not say "not eligible"
            if 'not eligible' in exp_lower or 'ineligible' in exp_lower:
                logger.warning("Explanation contradicts eligible=true decision")
                return False
        else:
            # If ineligible, should not say "eligible" without qualification
            if 'you are eligible' in exp_lower and 'not' not in exp_lower:
                logger.warning("Explanation contradicts eligible=false decision")
                return False

        return True

    def explain_eligibility(self, result: Dict[str, Any], language: str = "hi") -> str:
        """
        Generate simple explanation of verified eligibility result.

        Args:
            result: IntegrationResult dictionary with:
                - eligible: bool
                - scheme: str
                - age: Optional[int]
                - has_bpl: Optional[bool]
                - reason: str
                - missing_data: List[str]
            language: "en" or "hi"

        Returns:
            Simple 2-3 sentence explanation in specified language
        """
        if not self.enabled:
            return self._get_fallback_explanation(result.get('eligible'), language)

        try:
            # Extract result fields
            eligible = result.get('eligible', False)
            scheme = result.get('scheme', 'योजना')
            age = result.get('age')
            has_bpl = result.get('has_bpl')
            reason = result.get('reason', '')
            missing_data = result.get('missing_data', [])

            # Build user prompt with verified data only
            if language == "hi":
                system_prompt = self.SYSTEM_PROMPT_HI
                user_prompt = f"""इस पात्रता परिणाम की व्याख्या सरल हिंदी में करें:

योग्य: {eligible}
योजना: {scheme}
उम्र: {age}
BPL: {has_bpl}
कारण: {reason}
अधूरी जानकारी: {missing_data}

इसे सरल रखें। 2-3 वाक्य। हिंदी में।"""
            else:
                system_prompt = self.SYSTEM_PROMPT_EN
                user_prompt = f"""Explain this eligibility result in simple English:

Eligible: {eligible}
Scheme: {scheme}
Age: {age}
Has BPL: {has_bpl}
Reason: {reason}
Missing Data: {missing_data}

Keep it simple. 2-3 sentences. In English."""

            # Call LLM
            response = openai.ChatCompletion.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )

            explanation = response.choices[0].message.content.strip()

            # Validate output
            if self._detect_hallucination(explanation):
                logger.warning(f"Hallucination detected in explanation: {explanation}")
                return self._get_fallback_explanation(eligible, language)

            if not self._validate_against_decision(explanation, eligible):
                logger.warning(f"Explanation contradicts decision: {explanation}")
                return self._get_fallback_explanation(eligible, language)

            logger.info(f"Generated explanation: {explanation[:100]}...")
            return explanation

        except Exception as e:
            logger.error(f"LLM error: {e}. Using fallback.")
            return self._get_fallback_explanation(result.get('eligible'), language)

    def explain_missing_data(self, missing_fields: List[str], language: str = "hi") -> str:
        """
        Explain which information is needed.

        Args:
            missing_fields: List of field names (age, bpl_status, etc.)
            language: "en" or "hi"

        Returns:
            Explanation requesting missing data
        """
        if not missing_fields:
            return ""

        if language == "hi":
            if len(missing_fields) == 1:
                field_names = {
                    'age': 'उम्र',
                    'bpl_status': 'BPL स्थिति',
                    'gender': 'लिंग',
                }
                field_name = field_names.get(missing_fields[0], missing_fields[0])
                return f"आपकी {field_name} पता नहीं है। योग्यता जानने के लिए {field_name} बताएं।"
            else:
                field_list = ", ".join([
                    {
                        'age': 'उम्र',
                        'bpl_status': 'BPL स्थिति',
                        'gender': 'लिंग',
                    }.get(f, f)
                    for f in missing_fields
                ])
                return f"आपकी जानकारी अधूरी है: {field_list}। कृपया ये सभी विवरण प्रदान करें।"
        else:
            if len(missing_fields) == 1:
                field_names = {
                    'age': 'age',
                    'bpl_status': 'BPL status',
                    'gender': 'gender',
                }
                field_name = field_names.get(missing_fields[0], missing_fields[0])
                return f"Your {field_name} is not available. Please provide your {field_name} to check eligibility."
            else:
                field_list = ", ".join(missing_fields)
                return f"Your information is incomplete: {field_list}. Please provide all details."

    def explain_action_plan(self, action_plan: List[Dict[str, Any]], language: str = "hi") -> str:
        """
        Convert action plan steps into narrative explanation.

        Args:
            action_plan: List of action steps with 'order', 'text_en', 'text_hi'
            language: "en" or "hi"

        Returns:
            Narrative explanation of action steps
        """
        if not action_plan:
            return ""

        try:
            text_key = 'text_hi' if language == 'hi' else 'text_en'
            steps = [f"{step.get('order', i+1)}. {step.get(text_key, '')}"
                    for i, step in enumerate(action_plan) if step.get(text_key)]

            return "\n".join(steps) if steps else ""

        except Exception as e:
            logger.error(f"Error explaining action plan: {e}")
            return ""

    def _get_fallback_explanation(self, eligible: Optional[bool], language: str = "hi") -> str:
        """
        Return safe fallback explanation when LLM unavailable.

        Args:
            eligible: Eligibility status
            language: "en" or "hi"

        Returns:
            Fallback explanation
        """
        if language == "hi":
            fallbacks = self.FALLBACK_EXPLANATIONS_HI
        else:
            fallbacks = self.FALLBACK_EXPLANATIONS_EN

        if eligible is True:
            return fallbacks['eligible_generic']
        elif eligible is False:
            return fallbacks['ineligible_generic']
        else:
            return fallbacks['cannot_determine']


# Initialize global explainer (will be instantiated in main.py)
explainer: Optional[LLMExplainer] = None


def explain_eligibility(result: Dict[str, Any], language: str = "hi") -> str:
    """
    Module-level helper function to generate simple explanation of verified eligibility result.
    Uses LLMExplainer if available or fallback.
    """
    global explainer
    if explainer is None:
        explainer = LLMExplainer()
    return explainer.explain_eligibility(result, language=language)


def init_llm_explainer(api_key: Optional[str] = None, model: str = "gpt-3.5-turbo"):
    """
    Initialize global LLM explainer.

    Args:
        api_key: OpenAI API key
        model: LLM model name
    """
    global explainer
    explainer = LLMExplainer(api_key=api_key, model=model)
    logger.info(f"LLM explainer initialized: enabled={explainer.enabled}, model={model}")
