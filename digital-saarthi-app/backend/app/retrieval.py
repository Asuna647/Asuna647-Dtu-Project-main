"""
Digital Saarthi Retrieval Layer — Lightweight Keyword-Based Matching

Not a vector DB. Simple keyword matching against scheme fields.
Gracefully returns all schemes if no match found (never returns empty list).
"""

from typing import List, Optional, Dict, Any
from app.knowledge_base import get_all_schemes, get_scheme_by_id


def find_schemes(query: str) -> List[Dict[str, Any]]:
    """
    Find schemes matching the query string using keyword matching.

    Rules:
    - Lowercase query, tokenize on spaces
    - Match against: name, short_name, category, description, eligibility_criteria
    - Return matching scheme records as plain dicts (JSON-serializable)
    - If no match, return all schemes (graceful degradation)

    Args:
        query: User query string (voice transcription or text)

    Returns:
        List of matching scheme records as dicts; never empty (at least all schemes)
    """
    query_lower = query.lower()
    tokens = set(query_lower.split())

    matched_schemes = []
    all_schemes = get_all_schemes()

    for scheme in all_schemes:
        # Build searchable text from scheme fields
        searchable_text = (
            f"{scheme['name']} "
            f"{scheme['short_name']} "
            f"{scheme['category']} "
            f"{scheme['description']} "
            f"{' '.join(scheme['eligibility_criteria'])} "
        ).lower()

        # Check if any query token appears in searchable text
        match_score = sum(1 for token in tokens if token in searchable_text)

        if match_score > 0:
            matched_schemes.append(scheme)

    # Graceful degradation: if no match, return all schemes
    if not matched_schemes:
        matched_schemes = all_schemes

    return matched_schemes
