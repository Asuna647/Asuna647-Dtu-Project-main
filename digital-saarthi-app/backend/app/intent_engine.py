"""
Intent Detection Engine for Digital Saarthi

Classifies user queries into intents (eligibility_check, scheme_info, application_help, general, unknown)
using rule-based keyword matching. Supports English, Hindi, and mixed language queries.
"""

import logging
import re
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

# Intent keyword dictionaries
INTENT_KEYWORDS = {
    "eligibility_check": {
        "en": [
            "eligible", "eligibility", "qualify", "qualification", "qualified",
            "check", "verify", "confirm",
            "age", "bpl", "below poverty", "old age"
        ],
        "hi": [
            "योग्य", "पात्र", "पात्रता",
            "जाँच", "सत्यापन", "पुष्टि",
            "आयु", "बीपीएल", "गरीबी रेखा", "वृद्धावस्था"
        ]
    },
    "scheme_info": {
        "en": [
            "tell", "about", "details", "information", "info",
            "how many", "how much", "benefits",
            "requirement", "documents", "criteria", "steps"
        ],
        "hi": [
            "बताओ", "बारे", "विवरण", "जानकारी", "सूचना",
            "कितना", "लाभ", "आवश्यकता", "दस्तावेज़", "मानदंड", "चरण"
        ]
    },
    "application_help": {
        "en": [
            "how to", "how do i", "how can i", "apply", "application",
            "register", "registration", "enroll", "enrollment", "submit",
            "process", "procedure", "help", "assistance", "support", "contact", "office"
        ],
        "hi": [
            "कैसे", "कैसे करूँ", "कैसे करें", "आवेदन", "आवेदन करें",
            "पंजीकरण", "पंजीकृत", "नामांकन", "जमा", "जमा करें",
            "प्रक्रिया", "मदद", "सहायता", "संपर्क", "कार्यालय", "दफ्तर"
        ]
    }
}

# Per-scheme keywords for matched_schemes population
SCHEME_KEYWORDS = {
    "ignoaps": {
        "en": ["pension", "old age", "vridha", "budha", "retired", "senior citizen", "60"],
        "hi": ["पेंशन", "वृद्धावस्था", "वृद्ध", "बुढ़ा", "सेवानिवृत्त", "वरिष्ठ", "60"]
    },
    "eshram": {
        "en": ["shram", "labour", "labor", "worker", "unorganized", "majdoor", "informal"],
        "hi": ["श्रम", "श्रमिक", "मजदूर", "असंगठित", "काम", "कार्य", "रोजगार"]
    },
    "pm_kisan": {
        "en": ["kisan", "farmer", "farm", "agriculture", "krishi", "cultivation", "land"],
        "hi": ["किसान", "कृषि", "खेत", "खेती", "कृषक", "भूमि", "जमीन"]
    }
}


def preprocess_query(query: str, language: str = "auto") -> str:
    """
    Normalize query text for intent matching.
    - Lowercase
    - Remove punctuation (except hyphens in words)
    - Strip whitespace
    - Remove duplicate spaces
    """
    if not query:
        return ""

    # Lowercase
    text = query.lower()

    # Remove punctuation but keep hyphens
    text = re.sub(r'[^\w\sऀ-ॿ-]', '', text)

    # Strip and collapse spaces
    text = ' '.join(text.split())

    return text


def detect_language(text: str) -> str:
    """
    Detect language: 'en', 'hi', 'mixed', or 'unknown'.
    Devanagari script range: U+0900 to U+097F
    """
    if not text:
        return "unknown"

    # Check for Devanagari script (Hindi)
    devanagari_count = sum(1 for c in text if 0x0900 <= ord(c) <= 0x097F)
    latin_count = sum(1 for c in text if c.isascii() and c.isalpha())

    total_alpha = devanagari_count + latin_count

    if total_alpha == 0:
        return "unknown"

    # Determine language based on character distribution
    devanagari_ratio = devanagari_count / total_alpha if total_alpha > 0 else 0
    latin_ratio = latin_count / total_alpha if total_alpha > 0 else 0

    if devanagari_ratio > 0.7:
        return "hi"
    elif latin_ratio > 0.7:
        return "en"
    elif devanagari_ratio > 0.1 and latin_ratio > 0.1:
        return "mixed"
    else:
        return "unknown"


def calculate_intent_scores(query: str, language: str = "auto") -> Dict[str, float]:
    """
    Score query against all intents.
    Returns dict: {intent_name: confidence_score}
    Confidence = (matched_keyword_weight / number_of_matched_keywords)
    Uses relative scoring instead of absolute
    """
    preprocessed = preprocess_query(query)

    if not preprocessed:
        return {
            "eligibility_check": 0.0,
            "scheme_info": 0.0,
            "application_help": 0.0,
            "general": 0.0,
            "unknown": 1.0,
        }

    # Auto-detect language if not specified
    if language == "auto":
        language = detect_language(query)

    scores = {}
    match_counts = {}

    # Count matches per intent
    for intent_name, keywords_by_lang in INTENT_KEYWORDS.items():
        match_count = 0

        # Get keywords for detected language(s)
        keywords_to_check = []
        if language in ["en", "mixed", "unknown"]:
            keywords_to_check.extend(keywords_by_lang.get("en", []))
        if language in ["hi", "mixed", "unknown"]:
            keywords_to_check.extend(keywords_by_lang.get("hi", []))

        # Count matches
        for keyword in keywords_to_check:
            if keyword in preprocessed:
                match_count += 1

        match_counts[intent_name] = match_count

    # Calculate scores based on match counts
    total_matches = sum(match_counts.values())

    if total_matches == 0:
        # No matches, all intents have zero confidence
        return {
            "eligibility_check": 0.0,
            "scheme_info": 0.0,
            "application_help": 0.0,
            "general": 0.0,
            "unknown": 0.0,
        }

    # Normalize: each intent score = its matches / total matches
    for intent_name in INTENT_KEYWORDS.keys():
        scores[intent_name] = min(match_counts[intent_name] / total_matches, 1.0)

    return scores


def find_matched_schemes(query: str, language: str = "auto") -> List[str]:
    """
    Find schemes matching the query based on scheme-specific keywords.
    Returns list of scheme IDs.
    """
    preprocessed = preprocess_query(query)

    if not preprocessed:
        return []

    # Auto-detect language
    if language == "auto":
        language = detect_language(query)

    matched = []

    for scheme_id, keywords_by_lang in SCHEME_KEYWORDS.items():
        keywords_to_check = []

        if language in ["en", "mixed", "unknown"]:
            keywords_to_check.extend(keywords_by_lang.get("en", []))
        if language in ["hi", "mixed", "unknown"]:
            keywords_to_check.extend(keywords_by_lang.get("hi", []))

        # Check if any keyword matches
        for keyword in keywords_to_check:
            if keyword in preprocessed:
                matched.append(scheme_id)
                break  # Don't add same scheme twice

    return matched if matched else []


def detect_intent(query: str, language: str = "auto") -> Dict[str, Any]:
    """
    Detect intent from query.
    Returns dict with: intent, confidence, matched_schemes, reasoning, ambiguous, top_alternatives
    """
    # Preprocess
    preprocessed = preprocess_query(query)

    if not preprocessed:
        return {
            "intent": "unknown",
            "confidence": 0.0,
            "matched_schemes": [],
            "reasoning": "Query is empty or contains no meaningful text.",
            "ambiguous": False,
            "top_alternatives": [],
        }

    # Detect language
    if language == "auto":
        language = detect_language(query)

    # Calculate scores
    intent_scores = calculate_intent_scores(query, language)

    # Find matched schemes
    matched_schemes = find_matched_schemes(query, language)

    # Sort intents by confidence (descending)
    sorted_intents = sorted(intent_scores.items(), key=lambda x: x[1], reverse=True)

    top_intent = sorted_intents[0][0]
    top_confidence = sorted_intents[0][1]

    # Check for ambiguity (top 2 intents within ±0.05)
    ambiguous = False
    top_alternatives = []

    if len(sorted_intents) > 1:
        second_intent = sorted_intents[1][0]
        second_confidence = sorted_intents[1][1]

        if top_confidence > 0 and abs(top_confidence - second_confidence) <= 0.05:
            ambiguous = True
            # Include top 3 alternatives if ambiguous
            top_alternatives = [
                {
                    "intent": sorted_intents[i][0],
                    "confidence": sorted_intents[i][1],
                }
                for i in range(min(3, len(sorted_intents)))
            ]

    # Build reasoning
    if top_confidence == 0.0:
        reasoning = "No matching keywords detected. Intent unknown."
    else:
        matched_keywords = []
        for keyword in INTENT_KEYWORDS.get(top_intent, {}).get(language, []):
            if keyword in preprocessed:
                matched_keywords.append(keyword)

        reasoning = f"Matched keywords: {', '.join(matched_keywords[:3])}. "
        if matched_schemes:
            reasoning += f"Schemes: {', '.join(matched_schemes)}."

    return {
        "intent": top_intent,
        "confidence": top_confidence,
        "matched_schemes": matched_schemes,
        "reasoning": reasoning.strip(),
        "ambiguous": ambiguous,
        "top_alternatives": top_alternatives,
    }
