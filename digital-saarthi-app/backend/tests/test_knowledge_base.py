"""
Tests for Knowledge Base and Retrieval Layer

Covers:
- All three scheme IDs present
- Source verification metadata
- Official URLs correctness
- Retrieval keyword matching
- Graceful degradation
"""

import pytest
from app.knowledge_base import get_all_schemes, get_scheme_by_id
from app.retrieval import find_schemes


class TestKnowledgeBaseStructure:
    """Test knowledge base has all required schemes and fields."""

    def test_all_three_schemes_present(self):
        """All three scheme IDs should be present."""
        schemes = get_all_schemes()
        ids = [s["id"] for s in schemes]
        assert "ignoaps" in ids
        assert "eshram" in ids
        assert "pm_kisan" in ids

    def test_each_scheme_has_official_url(self):
        """Each scheme must have a non-empty official_url starting with https://."""
        schemes = get_all_schemes()
        for scheme in schemes:
            url = scheme["source"]["official_url"]
            assert url, f"{scheme['id']} missing official_url"
            assert url.startswith("https://"), f"{scheme['id']} URL must start with https://"

    def test_each_scheme_has_department(self):
        """Each scheme must have a non-empty department string."""
        schemes = get_all_schemes()
        for scheme in schemes:
            dept = scheme["source"]["department"]
            assert dept, f"{scheme['id']} missing department"
            assert isinstance(dept, str)

    def test_each_scheme_has_last_verified(self):
        """Each scheme must have last_verified as valid ISO date."""
        schemes = get_all_schemes()
        for scheme in schemes:
            date = scheme["source"]["last_verified"]
            assert date, f"{scheme['id']} missing last_verified"
            # Basic ISO date format check YYYY-MM-DD
            assert len(date) == 10
            assert date[4] == "-" and date[7] == "-"

    def test_each_scheme_has_required_lists(self):
        """Each scheme must have at least one item in key lists."""
        schemes = get_all_schemes()
        for scheme in schemes:
            assert len(scheme["eligibility_criteria"]) >= 1, f"{scheme['id']} missing eligibility_criteria"
            assert len(scheme["required_documents"]) >= 1, f"{scheme['id']} missing required_documents"
            assert len(scheme["benefits"]) >= 1, f"{scheme['id']} missing benefits"
            assert len(scheme["steps"]) >= 1, f"{scheme['id']} missing steps"


class TestOfficialURLs:
    """Test official URLs are correct and real."""

    def test_ignoaps_official_url(self):
        """IGNOAPS URL must point to nsap.nic.in."""
        scheme = get_scheme_by_id("ignoaps")
        assert "nsap.nic.in" in scheme["source"]["official_url"]

    def test_eshram_official_url(self):
        """E-Shram URL must point to eshram.gov.in."""
        scheme = get_scheme_by_id("eshram")
        assert "eshram.gov.in" in scheme["source"]["official_url"]

    def test_pm_kisan_official_url(self):
        """PM-Kisan URL must point to pmkisan.gov.in."""
        scheme = get_scheme_by_id("pm_kisan")
        assert "pmkisan.gov.in" in scheme["source"]["official_url"]


class TestHelplines:
    """Test helpline numbers are present for key schemes."""

    def test_ignoaps_has_helpline(self):
        """IGNOAPS must have Elder helpline 14567."""
        scheme = get_scheme_by_id("ignoaps")
        assert scheme["source"]["helpline"] == "14567"

    def test_eshram_has_helpline(self):
        """E-Shram must have helpline 14434."""
        scheme = get_scheme_by_id("eshram")
        assert scheme["source"]["helpline"] == "14434"

    def test_pm_kisan_has_helpline(self):
        """PM-Kisan must have helpline 155261."""
        scheme = get_scheme_by_id("pm_kisan")
        assert scheme["source"]["helpline"] == "155261"


class TestSchemeLookup:
    """Test get_scheme_by_id function."""

    def test_get_ignoaps_by_id(self):
        """Lookup IGNOAPS by ID returns correct record."""
        scheme = get_scheme_by_id("ignoaps")
        assert scheme is not None
        assert scheme["id"] == "ignoaps"

    def test_get_eshram_by_id(self):
        """Lookup E-Shram by ID returns correct record."""
        scheme = get_scheme_by_id("eshram")
        assert scheme is not None
        assert scheme["id"] == "eshram"

    def test_get_pm_kisan_by_id(self):
        """Lookup PM-Kisan by ID returns correct record."""
        scheme = get_scheme_by_id("pm_kisan")
        assert scheme is not None
        assert scheme["id"] == "pm_kisan"

    def test_get_invalid_scheme_returns_none(self):
        """Lookup invalid ID returns None."""
        scheme = get_scheme_by_id("invalid_scheme")
        assert scheme is None

    def test_case_insensitive_lookup(self):
        """Lookup should be case-insensitive."""
        scheme = get_scheme_by_id("IGNOAPS")
        assert scheme is not None
        assert scheme["id"] == "ignoaps"


class TestRetrieval:
    """Test keyword-based scheme retrieval."""

    def test_find_pension_returns_ignoaps(self):
        """Query 'pension' must return IGNOAPS."""
        results = find_schemes("pension")
        ids = [s["id"] for s in results]
        assert "ignoaps" in ids

    def test_find_kisan_returns_pm_kisan(self):
        """Query 'kisan' must return PM-Kisan."""
        results = find_schemes("kisan")
        ids = [s["id"] for s in results]
        assert "pm_kisan" in ids

    def test_find_shram_returns_eshram(self):
        """Query 'shram' must return E-Shram."""
        results = find_schemes("shram")
        ids = [s["id"] for s in results]
        assert "eshram" in ids

    def test_find_unknown_returns_all_schemes(self):
        """Unknown query returns all schemes (graceful degradation)."""
        results = find_schemes("xyz123_completely_unknown_query")
        assert len(results) == 3  # All three schemes

    def test_find_empty_query_returns_all(self):
        """Empty query returns all schemes."""
        results = find_schemes("")
        assert len(results) == 3

    def test_find_hindi_keyword_works(self):
        """Hindi keyword 'vridha' should match pension scheme."""
        results = find_schemes("vridha pension")
        ids = [s["id"] for s in results]
        assert "ignoaps" in ids


class TestBenefitsAccuracy:
    """Test benefits contain only verified facts, no invented amounts."""

    def test_ignoaps_benefits_mention_variance(self):
        """IGNOAPS benefits must mention that amount varies by state."""
        scheme = get_scheme_by_id("ignoaps")
        benefits_text = " ".join(scheme["benefits"]).lower()
        # Should NOT state a single fixed amount
        # Should mention "varies" or "state"
        assert "varies" in benefits_text or "state" in benefits_text

    def test_pm_kisan_benefits_are_correct(self):
        """PM-Kisan benefits must be ₹6,000 per year, ₹2,000 per instalment."""
        scheme = get_scheme_by_id("pm_kisan")
        benefits_text = " ".join(scheme["benefits"])
        assert "6,000" in benefits_text or "6000" in benefits_text
