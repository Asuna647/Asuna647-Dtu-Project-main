"""
Stage 8 Tests: Accessibility & UI Polish
"""

import pytest
from app.accessibility_validator import AccessibilityValidator


class TestAccessibilityContrast:
    """Test contrast ratio validation."""

    def test_high_contrast_black_white(self):
        """Black on white has excellent contrast."""
        ratio, compliant = AccessibilityValidator.check_contrast_ratio("#000000", "#ffffff")
        assert ratio >= 21.0
        assert compliant is True

    def test_wcag_aa_minimum_contrast(self):
        """4.5:1 meets WCAG AA standard."""
        ratio, compliant = AccessibilityValidator.check_contrast_ratio("#333333", "#ffffff")
        assert ratio >= 4.5
        assert compliant is True

    def test_low_contrast_fails(self):
        """Low contrast fails validation."""
        ratio, compliant = AccessibilityValidator.check_contrast_ratio("#cccccc", "#ffffff")
        assert ratio < 4.5
        assert compliant is False


class TestAccessibilityKeyboardNavigation:
    """Test keyboard navigation."""

    def test_keyboard_navigation_valid(self):
        """Valid keyboard navigation structure."""
        result = AccessibilityValidator.check_keyboard_navigation(10)

        assert result["tab_order_logical"] is True
        assert result["focus_visible"] is True
        assert len(result["keyboard_traps"]) == 0


class TestAccessibilityAriaLabels:
    """Test ARIA labels for screen readers."""

    def test_aria_coverage_excellent(self):
        """95%+ ARIA label coverage."""
        result = AccessibilityValidator.check_aria_labels(95, 100)

        assert result["coverage_percent"] == 95.0
        assert result["compliant"] is True

    def test_aria_coverage_poor(self):
        """Low ARIA coverage fails."""
        result = AccessibilityValidator.check_aria_labels(70, 100)

        assert result["coverage_percent"] == 70.0
        assert result["compliant"] is False


class TestAccessibilityAltText:
    """Test alt text on images."""

    def test_alt_text_complete(self):
        """All images have alt text."""
        result = AccessibilityValidator.check_alt_text(10, 10)

        assert result["coverage_percent"] == 100.0
        assert result["compliant"] is True

    def test_alt_text_missing(self):
        """Missing alt text fails."""
        result = AccessibilityValidator.check_alt_text(10, 8)

        assert result["coverage_percent"] == 80.0
        assert result["compliant"] is False


class TestAccessibilityFontSizes:
    """Test readable font sizes."""

    def test_font_sizes_compliant(self):
        """Large fonts meet accessibility standards."""
        result = AccessibilityValidator.check_font_sizes(18, 32, 24)

        assert result["body_compliant"] is True
        assert result["heading_compliant"] is True
        assert result["compliant"] is True

    def test_font_sizes_too_small(self):
        """Small fonts fail validation."""
        result = AccessibilityValidator.check_font_sizes(12, 18, 16)

        assert result["body_compliant"] is False
        assert result["compliant"] is False


class TestAccessibilityTouchTargets:
    """Test touch target sizes."""

    def test_touch_targets_compliant(self):
        """48×48px meets accessibility standards."""
        result = AccessibilityValidator.check_touch_targets(56, 56)

        assert result["compliant"] is True

    def test_touch_targets_too_small(self):
        """Small touch targets fail."""
        result = AccessibilityValidator.check_touch_targets(40, 40)

        assert result["compliant"] is False


class TestAccessibilityAudit:
    """Test full accessibility audit."""

    def test_audit_perfect_score(self):
        """Perfect accessibility compliance."""
        result = AccessibilityValidator.audit_full_page(
            contrast_compliant=True,
            aria_coverage=100.0,
            alt_text_coverage=100.0,
            font_sizes_ok=True,
            touch_targets_ok=True,
            responsive=True
        )

        assert result["score"] >= 90
        assert result["level"] == "AA"
        assert result["compliant"] is True
        assert len(result["issues"]) == 0

    def test_audit_issues_reported(self):
        """Issues detected and reported."""
        result = AccessibilityValidator.audit_full_page(
            contrast_compliant=False,
            aria_coverage=80.0,
            alt_text_coverage=100.0,
            font_sizes_ok=False,
            touch_targets_ok=True,
            responsive=True
        )

        assert result["score"] < 90
        assert len(result["issues"]) > 0
        assert any(i["severity"] == "error" for i in result["issues"])


class TestUIPolish:
    """Test UI polish aspects."""

    def test_responsive_design(self):
        """Mobile responsive design works."""
        result = AccessibilityValidator.check_mobile_responsiveness()

        assert result["mobile_320px"] is True
        assert result["tablet_768px"] is True
        assert result["desktop_1024px"] is True
        assert result["compliant"] is True
