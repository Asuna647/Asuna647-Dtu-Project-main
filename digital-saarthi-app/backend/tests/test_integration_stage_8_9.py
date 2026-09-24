"""
Stage 8 & 9 Integration Tests
"""

import pytest
from app.accessibility_validator import AccessibilityValidator
from app.scheme_rules import check_all_schemes


class TestStage8Integration:
    """Integration tests for accessibility and UI polish."""

    def test_accessibility_audit_workflow(self):
        """Full accessibility audit workflow."""
        # Check contrast
        ratio, contrast_ok = AccessibilityValidator.check_contrast_ratio("#000000", "#ffffff")
        assert contrast_ok is True

        # Check ARIA labels
        aria_result = AccessibilityValidator.check_aria_labels(95, 100)
        assert aria_result["compliant"] is True

        # Check alt text
        alt_result = AccessibilityValidator.check_alt_text(5, 5)
        assert alt_result["compliant"] is True

        # Full audit
        audit = AccessibilityValidator.audit_full_page(
            contrast_compliant=contrast_ok,
            aria_coverage=aria_result["coverage_percent"],
            alt_text_coverage=alt_result["coverage_percent"],
            font_sizes_ok=True,
            touch_targets_ok=True,
            responsive=True
        )

        assert audit["score"] >= 80
        assert audit["level"] == "AA"

    def test_demo_scenario_accessibility(self):
        """Demo scenario with accessibility compliance."""
        # Golden demo: 72-year-old woman
        audit = AccessibilityValidator.audit_full_page(
            contrast_compliant=True,
            aria_coverage=100.0,
            alt_text_coverage=100.0,
            font_sizes_ok=True,
            touch_targets_ok=True,
            responsive=True
        )

        assert audit["compliant"] is True
        assert len(audit["issues"]) == 0


class TestStage9Integration:
    """Integration tests for all three schemes."""

    def test_golden_demo_elderly_pension(self):
        """Golden demo: 72-year-old BPL woman asking about mother's pension."""
        results = check_all_schemes(
            age=72,
            has_bpl=True,
            occupation="Retired teacher"
        )

        # Should be eligible for IGNOAPS
        assert results["IGNOAPS"]["eligible"] is True
        assert results["IGNOAPS"]["confidence"] == 1.0
        assert results["ranked"][0] == "IGNOAPS"

        # Should have official sources
        assert "1800-180-1111" in results["IGNOAPS"]["helpline"]
        assert "nsap.nic.in" in results["IGNOAPS"]["url"]

    def test_e_shram_street_vendor(self):
        """E-Shram: Street vendor scenario."""
        results = check_all_schemes(
            age=35,
            is_organised_worker=False,
            occupation="Street vendor",
            annual_income=12000
        )

        # Should be eligible for E-Shram
        assert results["E-Shram"]["eligible"] is True
        assert "Street vendor" in results["E-Shram"]["reason"] or results["E-Shram"]["eligible"]

    def test_pm_kisan_farmer(self):
        """PM-Kisan: Small farmer scenario."""
        results = check_all_schemes(
            age=45,
            is_farmer=True,
            land_holding_hectares=1.5,
            annual_income=600000
        )

        # Should be eligible for PM-Kisan
        assert results["PM-Kisan"]["eligible"] is True
        assert "1.5" in results["PM-Kisan"]["reason"] or "Eligible" in results["PM-Kisan"]["reason"]

    def test_failure_demo_hallucination_prevention(self):
        """Failure demo: System refuses to invent benefits."""
        results = check_all_schemes(age=65, has_bpl=True)

        # Should not invent amounts
        ignoaps_reason = results["IGNOAPS"]["reason"]
        assert "₹500" not in ignoaps_reason  # Never hardcode amount in reason
        assert "₹" not in ignoaps_reason  # No invented rupee amounts

    def test_scheme_ranking_logic(self):
        """Verify scheme ranking by eligibility."""
        # Eligible for multiple schemes
        results = check_all_schemes(
            age=55,
            has_bpl=True,
            is_farmer=True,
            land_holding_hectares=1.0
        )

        # All eligible schemes should be ranked before ineligible
        ranked = results["ranked"]
        for i, scheme in enumerate(ranked):
            is_eligible = results[scheme]["eligible"]
            # Once we hit an ineligible scheme, all following should be ineligible
            for j in range(i + 1, len(ranked)):
                if not is_eligible:
                    assert not results[ranked[j]]["eligible"]

    def test_edge_case_no_information(self):
        """Edge case: User provides no information."""
        results = check_all_schemes()

        # System should handle gracefully
        assert "ranked" in results
        assert "recommendation" in results
        # At least one scheme should be checked
        assert len(results) >= 4  # 3 schemes + metadata

    def test_confidence_reflects_data_quality(self):
        """Confidence scores reflect data quality."""
        # High confidence with all data
        results_complete = check_all_schemes(
            age=65, has_bpl=True, is_farmer=False, is_organised_worker=False
        )
        ignoaps_confidence_complete = results_complete["IGNOAPS"]["confidence"]

        # Lower confidence with missing data
        results_incomplete = check_all_schemes(age=65, has_bpl=None)
        ignoaps_confidence_incomplete = results_incomplete["IGNOAPS"]["confidence"]

        assert ignoaps_confidence_complete >= ignoaps_confidence_incomplete


class TestStage9DemoScenarios:
    """Demo scenarios for hackathon judges."""

    def test_scenario_elderly_pension_inquiry(self):
        """Scenario: 72-year-old asking about mother's pension."""
        # User input: "Meri maa 72 saal ki hain. Unko pension mil sakti hai?"
        # Extracted: age=72, bpl=true, relation=mother

        results = check_all_schemes(age=72, has_bpl=True)

        # Check all requirements
        assert results["IGNOAPS"]["eligible"] is True
        assert results["eligible_count"] == 1
        assert results["recommendation"]

        # Verify sources
        assert "nsap.nic.in" in results["IGNOAPS"]["url"]
        assert "1800-180-1111" in results["IGNOAPS"]["helpline"]

    def test_scenario_farmer_subsidy(self):
        """Scenario: Farmer asking about government support."""
        results = check_all_schemes(
            age=50, is_farmer=True, land_holding_hectares=1.75
        )

        assert results["PM-Kisan"]["eligible"] is True

    def test_scenario_worker_insurance(self):
        """Scenario: Unorganized worker asking about insurance."""
        results = check_all_schemes(
            age=35, is_organised_worker=False, occupation="Street vendor"
        )

        assert results["E-Shram"]["eligible"] is True
