"""
Stage 9: Canonical Scheme Eligibility Rules Implementation

Single source of truth for IGNOAPS, E-Shram, and PM-Kisan scheme logic.
All scheme eligibility rules are verified against official government sources.
"""

from typing import Tuple, Optional, Dict, Any


def is_eligible_eshram(
    age: Optional[int] = None,
    annual_income: Optional[int] = None,
    is_organised_worker: bool = False,
    has_esic_coverage: bool = False,
    has_epf_coverage: bool = False,
    is_income_tax_payee: bool = False,
    occupation: Optional[str] = None
) -> Tuple[bool, str, float]:
    """
    Determine E-Shram eligibility for unorganized workers.

    Rule: Unorganized worker aged 16-59 years, not covered under EPFO/ESIC, not an income tax payee.
    Source URL: https://eshram.gov.in/faqs
    Verification Date: 2026-09-24
    Confidence Level: 1.0 (with required data), 0.5 (with missing age)

    Returns: (eligible: bool, reason: str, confidence: float)
    """
    # Rule as code comment:
    # E-Shram Rule: Workers in the unorganised sector aged between 16 and 59 years,
    # not covered under EPFO or ESIC, and not income tax payees are eligible for e-Shram.
    # Note: Official e-Shram FAQs specify NO mandatory annual income ceiling for registration.
    # Source URL: https://eshram.gov.in/faqs
    # Verification Date: 2026-09-24
    # Confidence Level: 1.0

    # Age check (16-59)
    if age is None:
        return (False, "Age is required to determine E-Shram eligibility", 0.5)

    if age < 16:
        return (False, f"Age {age} is below 16. E-Shram is for unorganized workers 16-59 years old.", 1.0)

    if age >= 60:
        return (False, f"Age {age} is 60 or older. E-Shram is for workers 16-59. Consider IGNOAPS pension scheme.", 1.0)

    # Cannot be organized sector worker or covered under EPFO/ESIC
    if is_organised_worker:
        return (False, "Organized sector workers are not eligible for E-Shram registration.", 1.0)

    if has_esic_coverage or has_epf_coverage:
        return (False, "Workers with ESIC or EPF coverage are not eligible for E-Shram. They have formal sector protection.", 1.0)

    # Income tax payee exclusion
    if is_income_tax_payee:
        return (False, "Income tax payees are not eligible for E-Shram registration.", 1.0)

    # All checks passed
    reason = f"Eligible for E-Shram: Age {age} (16-59), unorganized worker without ESIC/EPF or Income Tax payee exclusion"
    if occupation:
        reason += f", occupation: {occupation}"

    return (True, reason, 1.0)


def is_eligible_pm_kisan(
    age: Optional[int] = None,
    is_farmer: bool = False,
    land_holding_hectares: Optional[float] = None,
    is_government_employee: bool = False,
    is_class_iv_employee: bool = False,
    is_income_tax_payee: bool = False,
    monthly_pension: Optional[int] = None,
    is_institutional_landholder: bool = False,
    is_registered_professional: bool = False,
    previous_year_income: Optional[int] = None,
    occupation: Optional[str] = None
) -> Tuple[bool, str, float]:
    """
    Determine PM-Kisan eligibility for landholding farmer families.

    Rule: All landholding farmer families with cultivable land (>0 ha) are eligible,
    subject to exclusion categories (institutional landholders, govt employees except Class IV/Group D,
    income tax payees, monthly pension >= ₹10,000, and registered professionals).
    Source URL: https://www.pmkisan.gov.in/
    Verification Date: 2026-09-24
    Confidence Level: 1.0 (with required data), 0.5 (with missing land holding)

    Returns: (eligible: bool, reason: str, confidence: float)
    """
    # Rule as code comment:
    # PM-Kisan Rule: Scheme covers all landholding farmer families with cultivable land (>0 hectares),
    # regardless of size (2-hectare upper limit was removed in June 2019).
    # Subject to exclusions: Institutional landholders, constitutional post holders, serving/retired
    # government employees (except Class IV/Group D/MTS), income tax payees, pensioners >= ₹10k/mo,
    # and registered professionals (doctors, engineers, lawyers, CAs, architects).
    # Source URL: https://www.pmkisan.gov.in/
    # Verification Date: 2026-09-24
    # Confidence Level: 1.0

    # Must be a farmer
    if not is_farmer:
        occupation_str = f"({occupation})" if occupation else "(not specified)"
        return (False, f"Not a farmer {occupation_str}. PM-Kisan is exclusively for landholding farmer families.", 1.0)

    # Land holding check (> 0 hectares)
    if land_holding_hectares is None:
        return (False, "Land holding size is required for PM-Kisan eligibility verification.", 0.5)

    if land_holding_hectares <= 0:
        return (False, f"Land holding {land_holding_hectares} hectares is invalid. Must own cultivable land (> 0 ha).", 1.0)

    # Exclusion checks
    if is_institutional_landholder:
        return (False, "Institutional landholders are excluded from PM-Kisan benefits.", 1.0)

    if is_government_employee and not is_class_iv_employee:
        return (False, "Serving or retired government employees (except Class IV / Group D / MTS employees) are excluded from PM-Kisan.", 1.0)

    if is_income_tax_payee:
        return (False, "Income tax payees in the last assessment year are excluded from PM-Kisan.", 1.0)

    if monthly_pension is not None and monthly_pension >= 10000 and not is_class_iv_employee:
        return (False, f"Retired pensioners with monthly pension ₹{monthly_pension} (>= ₹10,000) are excluded from PM-Kisan.", 1.0)

    if is_registered_professional:
        return (False, "Registered professionals (doctors, engineers, lawyers, CAs, architects) are excluded from PM-Kisan.", 1.0)

    # All checks passed
    reason = f"Eligible for PM-Kisan: Landholding farmer family with {land_holding_hectares} hectares cultivable land holding, no exclusion criteria triggered"
    return (True, reason, 1.0)


def check_all_schemes(
    age: Optional[int] = None,
    has_bpl: Optional[bool] = None,
    is_organised_worker: Optional[bool] = None,
    is_farmer: Optional[bool] = None,
    land_holding_hectares: Optional[float] = None,
    occupation: Optional[str] = None,
    annual_income: Optional[int] = None,
    is_government_employee: bool = False,
    is_income_tax_payee: bool = False,
    has_esic_coverage: bool = False,
    has_epf_coverage: bool = False
) -> Dict[str, Any]:
    """
    Check eligibility for all 3 schemes simultaneously.

    Returns multi-scheme comparison with ranking.
    """
    results = {}

    # Check IGNOAPS (Age >= 60 AND BPL)
    # Rule as code comment:
    # IGNOAPS Rule: Senior citizens aged 60 years or above belonging to Below Poverty Line (BPL) households.
    # Source URL: https://nsap.nic.in
    # Verification Date: 2026-09-24
    # Confidence Level: 1.0
    ignoaps_eligible = False
    ignoaps_reason = ""
    ignoaps_confidence = 0.5

    if age is not None:
        if age >= 60 and has_bpl is True:
            ignoaps_eligible = True
            ignoaps_reason = f"Eligible for IGNOAPS: Age {age} >= 60 and BPL status confirmed."
            ignoaps_confidence = 1.0
        elif age >= 60 and has_bpl is None:
            ignoaps_eligible = False
            ignoaps_reason = f"Age {age} qualifies for IGNOAPS, but BPL status needs verification."
            ignoaps_confidence = 0.7
        elif age >= 60:
            ignoaps_eligible = False
            ignoaps_reason = f"Age {age} >= 60 qualifies, but not BPL (Below Poverty Line)."
            ignoaps_confidence = 1.0
        else:
            ignoaps_eligible = False
            ignoaps_reason = f"Age {age} is below 60 minimum required for IGNOAPS pension."
            ignoaps_confidence = 1.0
    else:
        ignoaps_eligible = False
        ignoaps_reason = "Age is required to determine IGNOAPS eligibility."
        ignoaps_confidence = 0.5

    results["IGNOAPS"] = {
        "eligible": ignoaps_eligible,
        "confidence": ignoaps_confidence,
        "reason": ignoaps_reason,
        "monthly_benefit": "₹500 (central) + state pension support",
        "helpline": "1800-180-1111",
        "url": "https://nsap.nic.in"
    }

    # Check E-Shram
    eshram_eligible, eshram_reason, eshram_confidence = is_eligible_eshram(
        age=age,
        annual_income=annual_income,
        is_organised_worker=is_organised_worker or False,
        has_esic_coverage=has_esic_coverage,
        has_epf_coverage=has_epf_coverage,
        is_income_tax_payee=is_income_tax_payee,
        occupation=occupation
    )

    results["E-Shram"] = {
        "eligible": eshram_eligible,
        "confidence": eshram_confidence,
        "reason": eshram_reason,
        "benefits": "Accident Insurance (₹2 Lakhs) + Social Security Card",
        "helpline": "1800-110-005",
        "url": "https://eshram.gov.in"
    }

    # Check PM-Kisan
    pmkisan_eligible, pmkisan_reason, pmkisan_confidence = is_eligible_pm_kisan(
        age=age,
        is_farmer=is_farmer or False,
        land_holding_hectares=land_holding_hectares,
        is_government_employee=is_government_employee,
        is_income_tax_payee=is_income_tax_payee,
        previous_year_income=annual_income,
        occupation=occupation
    )

    results["PM-Kisan"] = {
        "eligible": pmkisan_eligible,
        "confidence": pmkisan_confidence,
        "reason": pmkisan_reason,
        "monthly_benefit": "₹6,000/year (3 installments of ₹2,000)",
        "helpline": "1800-270-0888",
        "url": "https://pmkisan.gov.in"
    }

    # Ranking: eligible schemes first, then by confidence
    eligible_schemes = [s for s in ["IGNOAPS", "E-Shram", "PM-Kisan"] if results[s]["eligible"]]
    ineligible_schemes = [s for s in ["IGNOAPS", "E-Shram", "PM-Kisan"] if not results[s]["eligible"]]

    eligible_schemes.sort(key=lambda s: results[s]["confidence"], reverse=True)
    ineligible_schemes.sort(key=lambda s: results[s]["confidence"], reverse=True)

    ranked = eligible_schemes + ineligible_schemes

    if eligible_schemes:
        if len(eligible_schemes) == 1:
            recommendation = f"You are eligible for {eligible_schemes[0]}. This scheme best matches your profile."
        else:
            recommendation = f"You are eligible for multiple schemes: {', '.join(eligible_schemes)}. Choose the ones that best suit your needs."
    else:
        recommendations_to_check = [s for s in ranked if results[s]["confidence"] >= 0.7]
        if recommendations_to_check:
            recommendation = f"Currently not eligible for any scheme. To explore options, verify: {', '.join(recommendations_to_check)}"
        else:
            recommendation = "Not eligible for any scheme currently. Provide more information to check further options."

    results["ranked"] = ranked
    results["recommendation"] = recommendation
    results["eligible_count"] = len(eligible_schemes)

    return results
