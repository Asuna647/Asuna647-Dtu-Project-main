"""
Stage 9 Tests: E-Shram & PM-Kisan Schemes
"""

import pytest
from app.scheme_rules import is_eligible_eshram, is_eligible_pm_kisan, check_all_schemes


class TestEShramEligibility:
    """Test E-Shram scheme eligibility."""

    def test_eshram_age_18_eligible(self):
        """Age 18 is minimum eligible age."""
        eligible, reason, confidence = is_eligible_eshram(age=18)
        assert eligible is True
        assert confidence == 1.0

    def test_eshram_age_59_eligible(self):
        """Age 59 is maximum eligible age."""
        eligible, reason, confidence = is_eligible_eshram(age=59)
        assert eligible is True
        assert confidence == 1.0

    def test_eshram_age_17_ineligible(self):
        """Age below 18 ineligible."""
        eligible, reason, confidence = is_eligible_eshram(age=17)
        assert eligible is False
        assert "below 18" in reason.lower()

    def test_eshram_age_60_ineligible(self):
        """Age 60 and above ineligible."""
        eligible, reason, confidence = is_eligible_eshram(age=60)
        assert eligible is False
        assert "60 or older" in reason.lower()

    def test_eshram_no_age_required(self):
        """Age is required field."""
        eligible, reason, confidence = is_eligible_eshram(age=None)
        assert eligible is False
        assert "required" in reason.lower()

    def test_eshram_esic_ineligible(self):
        """ESIC coverage makes ineligible."""
        eligible, reason, confidence = is_eligible_eshram(age=30, has_esic_coverage=True)
        assert eligible is False
        assert "ESIC" in reason

    def test_eshram_epf_ineligible(self):
        """EPF coverage makes ineligible."""
        eligible, reason, confidence = is_eligible_eshram(age=30, has_epf_coverage=True)
        assert eligible is False
        assert "EPF" in reason

    def test_eshram_income_limit(self):
        """Income above ₹15,000 makes ineligible."""
        eligible, reason, confidence = is_eligible_eshram(age=30, annual_income=20000)
        assert eligible is False
        assert "20000" in reason

    def test_eshram_organised_worker_ineligible(self):
        """Organized sector workers ineligible."""
        eligible, reason, confidence = is_eligible_eshram(age=30, is_organised_worker=True)
        assert eligible is False
        assert "organized" in reason.lower()

    def test_eshram_occupation_included(self):
        """Occupation included in reason."""
        eligible, reason, confidence = is_eligible_eshram(age=30, occupation="Street vendor")
        assert eligible is True
        assert "Street vendor" in reason


class TestPMKisanEligibility:
    """Test PM-Kisan scheme eligibility."""

    def test_pmkisan_farmer_required(self):
        """Must be farmer."""
        eligible, reason, confidence = is_eligible_pm_kisan(is_farmer=False)
        assert eligible is False
        assert "farmer" in reason.lower()

    def test_pmkisan_land_holding_required(self):
        """Land holding required."""
        eligible, reason, confidence = is_eligible_pm_kisan(age=30, is_farmer=True, land_holding_hectares=None)
        assert eligible is False
        assert "required" in reason.lower()

    def test_pmkisan_min_land_0_5(self):
        """0.5 hectare minimum eligible."""
        eligible, reason, confidence = is_eligible_pm_kisan(
            age=30, is_farmer=True, land_holding_hectares=0.5
        )
        assert eligible is True

    def test_pmkisan_max_land_2_0(self):
        """2.0 hectare maximum eligible."""
        eligible, reason, confidence = is_eligible_pm_kisan(
            age=30, is_farmer=True, land_holding_hectares=2.0
        )
        assert eligible is True

    def test_pmkisan_land_below_zero(self):
        """Land holdings below 0 invalid."""
        eligible, reason, confidence = is_eligible_pm_kisan(
            age=30, is_farmer=True, land_holding_hectares=-0.5
        )
        assert eligible is False
        assert "invalid" in reason.lower()

    def test_pmkisan_land_exceeds_2(self):
        """Land holdings above 2 hectares ineligible."""
        eligible, reason, confidence = is_eligible_pm_kisan(
            age=30, is_farmer=True, land_holding_hectares=2.5
        )
        assert eligible is False
        assert "exceeds 2 hectare" in reason

    def test_pmkisan_income_limit(self):
        """Income above ₹15 lakh makes ineligible."""
        eligible, reason, confidence = is_eligible_pm_kisan(
            age=30, is_farmer=True, land_holding_hectares=1.0, previous_year_income=2000000
        )
        assert eligible is False
        assert "₹15 lakh" in reason

    def test_pmkisan_no_age_limit(self):
        """No age limit for PM-Kisan (unlike E-Shram)."""
        # Young farmer
        eligible1, _, _ = is_eligible_pm_kisan(age=20, is_farmer=True, land_holding_hectares=1.0)
        assert eligible1 is True

        # Old farmer
        eligible2, _, _ = is_eligible_pm_kisan(age=75, is_farmer=True, land_holding_hectares=1.0)
        assert eligible2 is True


class TestMultiSchemeComparison:
    """Test multi-scheme eligibility checking."""

    def test_elderly_bpl_ignoaps_only(self):
        """72-year-old BPL eligible for IGNOAPS only."""
        results = check_all_schemes(age=72, has_bpl=True)

        assert results["IGNOAPS"]["eligible"] is True
        assert results["E-Shram"]["eligible"] is False
        assert results["PM-Kisan"]["eligible"] is False
        assert results["ranked"][0] == "IGNOAPS"

    def test_young_farmer_pmkisan_only(self):
        """30-year-old farmer eligible for PM-Kisan only."""
        results = check_all_schemes(
            age=30, is_farmer=True, land_holding_hectares=1.0, has_bpl=False
        )

        assert results["PM-Kisan"]["eligible"] is True
        assert results["IGNOAPS"]["eligible"] is False
        # E-Shram eligible because age in range, but PM-Kisan ranked higher
        assert results["E-Shram"]["eligible"] is True
        assert results["ranked"][0] in ["PM-Kisan", "E-Shram"]  # Both eligible, either can be first

    def test_young_unorganized_worker_eshram(self):
        """25-year-old unorganized worker eligible for E-Shram."""
        results = check_all_schemes(
            age=25, is_organised_worker=False, occupation="Street vendor"
        )

        assert results["E-Shram"]["eligible"] is True
        assert results["ranked"][0] == "E-Shram"

    def test_multiple_eligibility(self):
        """User eligible for multiple schemes."""
        results = check_all_schemes(
            age=55, has_bpl=True, is_farmer=True, land_holding_hectares=1.5
        )

        eligible_schemes = [s for s in results["ranked"] if results[s]["eligible"]]
        assert len(eligible_schemes) >= 1

    def test_no_eligibility(self):
        """User not eligible for any scheme."""
        results = check_all_schemes(
            age=50, has_bpl=False, is_farmer=False, is_organised_worker=True
        )

        assert results["IGNOAPS"]["eligible"] is False
        assert results["E-Shram"]["eligible"] is False
        assert results["PM-Kisan"]["eligible"] is False
        assert results["eligible_count"] == 0

    def test_ranking_by_eligibility(self):
        """Eligible schemes ranked first."""
        results = check_all_schemes(
            age=72, has_bpl=True, is_farmer=True, land_holding_hectares=1.0
        )

        # First ranked should be eligible
        first_scheme = results["ranked"][0]
        assert results[first_scheme]["eligible"] is True

    def test_confidence_scores(self):
        """All schemes have confidence scores."""
        results = check_all_schemes(age=65, has_bpl=True)

        for scheme in ["IGNOAPS", "E-Shram", "PM-Kisan"]:
            assert "confidence" in results[scheme]
            assert 0.0 <= results[scheme]["confidence"] <= 1.0

    def test_helpline_numbers_present(self):
        """All schemes have helpline numbers."""
        results = check_all_schemes(age=65)

        assert "1800-180-1111" in results["IGNOAPS"]["helpline"]  # IGNOAPS
        assert "1800-110-005" in results["E-Shram"]["helpline"]   # E-Shram
        assert "1800-270-0888" in results["PM-Kisan"]["helpline"] # PM-Kisan

    def test_scheme_urls_present(self):
        """All schemes have official URLs."""
        results = check_all_schemes(age=50)

        assert results["IGNOAPS"]["url"] == "nsap.nic.in"
        assert results["E-Shram"]["url"] == "e-shram.in"
        assert results["PM-Kisan"]["url"] == "pmkisan.gov.in"

    def test_age_boundary_60(self):
        """Age 60 boundary: eligible for IGNOAPS, not E-Shram."""
        results = check_all_schemes(age=60, has_bpl=True)

        assert results["IGNOAPS"]["eligible"] is True
        assert results["E-Shram"]["eligible"] is False

    def test_age_boundary_59(self):
        """Age 59 boundary: eligible for E-Shram."""
        results = check_all_schemes(age=59, is_organised_worker=False)

        assert results["E-Shram"]["eligible"] is True

    def test_land_boundary_2_0_hectares(self):
        """Land 2.0 hectares: eligible for PM-Kisan."""
        results = check_all_schemes(
            age=40, is_farmer=True, land_holding_hectares=2.0
        )

        assert results["PM-Kisan"]["eligible"] is True

    def test_land_boundary_2_1_hectares(self):
        """Land 2.1 hectares: not eligible for PM-Kisan."""
        results = check_all_schemes(
            age=40, is_farmer=True, land_holding_hectares=2.1
        )

        assert results["PM-Kisan"]["eligible"] is False

    def test_recommendations_helpful(self):
        """Recommendations are helpful and specific."""
        results = check_all_schemes(age=72, has_bpl=True)

        recommendation = results["recommendation"]
        assert len(recommendation) > 0
        assert "IGNOAPS" in recommendation or "eligible" in recommendation.lower()
