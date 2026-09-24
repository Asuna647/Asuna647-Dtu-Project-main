import pytest
from app.rule_engine import check_ignoaps


# === ELIGIBILITY: POSITIVE CASES ===

def test_eligible_user_72_years_with_bpl():
    result = check_ignoaps(72, True)
    assert result.eligible is True
    assert result.confidence == 1.0
    assert "✓ Age" in result.reasons[0]
    assert "✓ BPL" in result.reasons[1]
    assert result.warning is None

def test_eligible_user_exactly_60_years():
    """Boundary: 60 is the minimum eligible age."""
    result = check_ignoaps(60, True)
    assert result.eligible is True
    assert result.verdict == "Eligible for IGNOAPS Pension"
    assert result.confidence == 1.0

def test_eligible_user_120_years():
    """Upper valid boundary."""
    result = check_ignoaps(120, True)
    assert result.eligible is True
    assert result.confidence == 1.0

def test_eligible_steps_are_actionable():
    result = check_ignoaps(72, True)
    assert len(result.steps) == 4
    for step in result.steps:
        assert step.startswith("Step")


# === ELIGIBILITY: NEGATIVE CASES ===

def test_not_eligible_age_59_with_bpl():
    """Boundary: 59 is one year below the threshold."""
    result = check_ignoaps(59, True)
    assert result.eligible is False
    assert "✗ Age" in result.reasons[0]
    assert result.confidence == 1.0

def test_not_eligible_age_45_with_bpl():
    result = check_ignoaps(45, True)
    assert result.eligible is False

def test_not_eligible_age_72_without_bpl():
    result = check_ignoaps(72, False)
    assert result.eligible is False
    assert "✗ BPL" in result.reasons[1]

def test_not_eligible_young_no_bpl():
    """Both criteria fail."""
    result = check_ignoaps(30, False)
    assert result.eligible is False
    assert "✗ Age" in result.reasons[0]
    assert "✗ BPL" in result.reasons[1]

def test_not_eligible_shows_bpl_steps_when_bpl_missing():
    result = check_ignoaps(72, False)
    assert result.eligible is False
    assert len(result.steps) > 0
    assert "BPL" in result.steps[1]

def test_not_eligible_no_steps_when_only_age_fails():
    result = check_ignoaps(50, True)
    assert result.eligible is False
    assert result.steps == []

def test_not_eligible_shows_warning():
    result = check_ignoaps(59, True)
    assert result.warning is not None
    assert "free" in result.warning.lower()


# === CANNOT DETERMINE: MISSING AGE ===

def test_cannot_determine_age_is_none():
    result = check_ignoaps(None, True)
    assert result.eligible is False
    assert result.verdict == "cannot_determine"
    assert result.confidence == 0.0
    assert result.steps == []

def test_cannot_determine_age_is_none_no_bpl():
    result = check_ignoaps(None, False)
    assert result.eligible is False
    assert result.verdict == "cannot_determine"
    assert result.confidence == 0.0


# === INVALID INPUT: OUT-OF-RANGE AGE ===

def test_invalid_negative_age():
    result = check_ignoaps(-1, True)
    assert result.eligible is False
    assert result.verdict == "invalid_input"
    assert result.confidence == 0.0
    assert "-1" in result.reasons[0]

def test_invalid_age_above_120():
    result = check_ignoaps(150, True)
    assert result.eligible is False
    assert result.verdict == "invalid_input"
    assert result.confidence == 0.0

def test_invalid_large_negative_age():
    result = check_ignoaps(-999, False)
    assert result.eligible is False
    assert result.verdict == "invalid_input"


# === EDGE CASES: ZERO AND BOUNDARY ===

def test_zero_age():
    result = check_ignoaps(0, True)
    assert result.eligible is False
    assert result.confidence == 1.0

def test_age_1():
    result = check_ignoaps(1, False)
    assert result.eligible is False
    assert result.confidence == 1.0


# === OUTPUT FORMAT ===

def test_reasons_are_human_readable():
    result = check_ignoaps(72, True)
    for reason in result.reasons:
        assert reason.startswith("✓") or reason.startswith("✗")

def test_scheme_always_ignoaps():
    for age in [None, -1, 0, 59, 60, 72, 150]:
        for bpl in [True, False]:
            result = check_ignoaps(age, bpl)
            assert result.scheme == "IGNOAPS"
