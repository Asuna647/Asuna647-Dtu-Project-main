"""
Stage 9 Tests: E-Shram & PM-Kisan Schemes
"""

import pytest
from app.scheme_rules import is_eligible_eshram, is_eligible_pm_kisan, check_all_schemes


class TestEShramEligibility:
    """Test E-Shram scheme eligibility against official government rules."""

    def test_eshram_age_16_eligible(self):
        """Age 16 is minimum eligible age."""
        eligible, reason, confidence = is_eligible_eshram(age=16)
        assert eligible is True
        assert confidence == 1.0

    def test_eshram_age_18_eligible(self):
        """Age 18 is eligible."""
        eligible, reason, confidence = is_eligible_eshram(age=18)
        assert eligible is True
        assert confidence == 1.0

    def test_eshram_age_59_eligible(self):
        """Age 59 is maximum eligible age."""
        eligible, reason, confidence = is_eligible_eshram(age=59)
        assert eligible is True
        assert confidence == 1.0

    def test_eshram_age_15_ineligible(self):
        """Age below 16 ineligible."""
        eligible, reason, confidence = is_eligible_eshram(age=15)
        assert eligible is False
        assert "below 16" in reason.lower()

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

    def test_eshram_income_tax_payee_ineligible(self):
        """Income tax payee makes ineligible."""
        eligible, reason, confidence = is_eligible_eshram(age=30, is_income_tax_payee=True)
        assert eligible is False
        assert "tax" in reason.lower()

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
    """Test PM-Kisan scheme eligibility against official government rules."""

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

    def test_pmkisan_land_above_2_0_eligible(self):
        """2.5 hectares land holding eligible (since June 2019 scheme expansion)."""
        eligible, reason, confidence = is_eligible_pm_kisan(
            age=30, is_farmer=True, land_holding_hectares=2.5
        )
        assert eligible is True

    def test_pmkisan_land_below_zero(self):
        """Land holdings below 0 invalid."""
        eligible, reason, confidence = is_eligible_pm_kisan(
            age=30, is_farmer=True, land_holding_hectares=-0.5
        )
        assert eligible is False
        assert "invalid" in reason.lower()

    def test_pmkisan_govt_employee_ineligible(self):
        """Serving or retired government employees (non Class IV) excluded."""
        eligible, reason, confidence = is_eligible_pm_kisan(
            age=30, is_farmer=True, land_holding_hectares=1.0, is_government_employee=True
        )
        assert eligible is False
        assert "government" in reason.lower()

    def test_pmkisan_income_tax_payee_ineligible(self):
        """Income tax payee excluded."""
        eligible, reason, confidence = is_eligible_pm_kisan(
            age=30, is_farmer=True, land_holding_hectares=1.0, is_income_tax_payee=True
        )
        assert eligible is False
        assert "tax" in reason.lower()

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
        """30-year-old farmer eligible for PM-Kisan."""
        results = check_all_schemes(
            age=30, is_farmer=True, land_holding_hectares=1.0, has_bpl=False
        )

        assert results["PM-Kisan"]["eligible"] is True
        assert results["IGNOAPS"]["eligible"] is False
        assert results["E-Shram"]["eligible"] is True
        assert results["ranked"][0] in ["PM-Kisan", "E-Shram"]

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

        assert "nsap.nic.in" in results["IGNOAPS"]["url"]
        assert "eshram.gov.in" in results["E-Shram"]["url"]
        assert "pmkisan.gov.in" in results["PM-Kisan"]["url"]

    def test_age_boundary_60(self):
        """Age 60 boundary: eligible for IGNOAPS, not E-Shram."""
        results = check_all_schemes(age=60, has_bpl=True)

        assert results["IGNOAPS"]["eligible"] is True
        assert results["E-Shram"]["eligible"] is False

    def test_age_boundary_59(self):
        """Age 59 boundary: eligible for E-Shram."""
        results = check_all_schemes(age=59, is_organised_worker=False)

        assert results["E-Shram"]["eligible"] is True

    def test_land_holding_large_farm(self):
        """Large land holding (5.0 hectares): eligible for PM-Kisan under current rules."""
        results = check_all_schemes(
            age=40, is_farmer=True, land_holding_hectares=5.0
        )

        assert results["PM-Kisan"]["eligible"] is True

    def test_recommendations_helpful(self):
        """Recommendations are helpful and specific."""
        results = check_all_schemes(age=72, has_bpl=True)

        recommendation = results["recommendation"]
        assert len(recommendation) > 0
        assert "IGNOAPS" in recommendation or "eligible" in recommendation.lower()
