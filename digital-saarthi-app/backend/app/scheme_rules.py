"""
Stage 9: E-Shram & PM-Kisan Rules Implementation

Complete government scheme eligibility determination.
"""

from typing import Tuple, Optional, Dict, Any


def is_eligible_eshram(
    age: Optional[int] = None,
    annual_income: Optional[int] = None,
    is_organised_worker: bool = False,
    has_esic_coverage: bool = False,
    has_epf_coverage: bool = False,
    occupation: Optional[str] = None
) -> Tuple[bool, str, float]:
    """
    Determine E-Shram eligibility for unorganized workers.

    Returns: (eligible: bool, reason: str, confidence: float)
    """

    # Age check (18-59)
    if age is None:
        return (False, "Age is required to determine E-Shram eligibility", 0.5)

    if age < 18:
        return (False, f"Age {age} is below 18. E-Shram is for workers 18-59 years old.", 1.0)

    if age >= 60:
        return (False, f"Age {age} is 60 or older. E-Shram is for workers 18-59. Consider IGNOAPS pension scheme.", 1.0)

    # Cannot be organized sector worker
    if is_organised_worker:
        return (False, "Organized sector workers are not eligible for E-Shram registration.", 1.0)

    if has_esic_coverage or has_epf_coverage:
        return (False, "Workers with ESIC or EPF coverage are not eligible for E-Shram. They have formal sector protection.", 1.0)

    # Income check (if provided)
    if annual_income is not None and annual_income > 15000:
        return (False, f"Annual income ₹{annual_income} exceeds ₹15,000 limit for E-Shram.", 1.0)

    # All checks passed
    reason = "Eligible for E-Shram: Age 18-59, unorganized worker without ESIC/EPF coverage"
    if occupation:
        reason += f", occupation: {occupation}"

    return (True, reason, 1.0)


def is_eligible_pm_kisan(
    age: Optional[int] = None,
    is_farmer: bool = False,
    land_holding_hectares: Optional[float] = None,
    is_government_employee: bool = False,
    previous_year_income: Optional[int] = None,
    occupation: Optional[str] = None
) -> Tuple[bool, str, float]:
    """
    Determine PM-Kisan eligibility for farmers.

    Returns: (eligible: bool, reason: str, confidence: float)
    """

    # Must be a farmer
    if not is_farmer:
        occupation_str = f"({occupation})" if occupation else "(not specified)"
        return (False, f"Not a farmer {occupation_str}. PM-Kisan is exclusively for farmers and cultivators.", 1.0)

    # Land holding check (0-2 hectares)
    if land_holding_hectares is None:
        return (False, "Land holding size is required for PM-Kisan eligibility verification.", 0.5)

    if land_holding_hectares <= 0:
        return (False, f"Land holding {land_holding_hectares} hectares is invalid. Must be greater than 0.", 1.0)

    if land_holding_hectares > 2:
        return (False, f"Land holding {land_holding_hectares} hectares exceeds 2 hectare limit for PM-Kisan.", 1.0)

    # Government employee check (with exceptions for Class IV/Group D)
    if is_government_employee:
        return (False, "Government employees typically not eligible. Exception: Class IV/Group D employees may be eligible but require verification.", 0.7)

    # Income check (if provided)
    if previous_year_income is not None and previous_year_income > 1500000:
        return (False, f"Previous year income ₹{previous_year_income} exceeds ₹15 lakh limit for PM-Kisan.", 1.0)

    # All checks passed
    reason = f"Eligible for PM-Kisan: Farmer with {land_holding_hectares} hectares land holding, income within limits"
    return (True, reason, 1.0)


def check_all_schemes(
    age: Optional[int] = None,
    has_bpl: Optional[bool] = None,
    is_organised_worker: Optional[bool] = None,
    is_farmer: Optional[bool] = None,
    land_holding_hectares: Optional[float] = None,
    occupation: Optional[str] = None,
    annual_income: Optional[int] = None,
    is_government_employee: bool = False
) -> Dict[str, Any]:
    """
    Check eligibility for all 3 schemes simultaneously.

    Returns multi-scheme comparison with ranking.
    """

    results = {}

    # Check IGNOAPS (Age >= 60 AND BPL)
    ignoaps_eligible = False
    ignoaps_reason = ""
    ignoaps_confidence = 0.5

    if age is not None:
        if age >= 60 and has_bpl is True:
            ignoaps_eligible = True
            ignoaps_reason = f"Eligible: Age {age} >= 60 and BPL status confirmed"
            ignoaps_confidence = 1.0
        elif age >= 60 and has_bpl is None:
            ignoaps_eligible = False
            ignoaps_reason = f"Age {age} qualifies, but BPL status needs verification"
            ignoaps_confidence = 0.7
        elif age >= 60:
            ignoaps_eligible = False
            ignoaps_reason = f"Age {age} >= 60 but not BPL (Below Poverty Line)"
            ignoaps_confidence = 1.0
        else:
            ignoaps_eligible = False
            ignoaps_reason = f"Age {age} is below 60 minimum for IGNOAPS"
            ignoaps_confidence = 1.0
    else:
        ignoaps_eligible = False
        ignoaps_reason = "Age is required to determine IGNOAPS eligibility"
        ignoaps_confidence = 0.5

    results["IGNOAPS"] = {
        "eligible": ignoaps_eligible,
        "confidence": ignoaps_confidence,
        "reason": ignoaps_reason,
        "monthly_benefit": "₹500 (central) + state support",
        "helpline": "1800-180-1111",
        "url": "nsap.nic.in"
    }

    # Check E-Shram
    eshram_eligible, eshram_reason, eshram_confidence = is_eligible_eshram(
        age=age,
        annual_income=annual_income,
        is_organised_worker=is_organised_worker or False,
        occupation=occupation
    )

    results["E-Shram"] = {
        "eligible": eshram_eligible,
        "confidence": eshram_confidence,
        "reason": eshram_reason,
        "benefits": "₹2L accident + ₹1L disability + ₹20K death",
        "helpline": "1800-110-005",
        "url": "e-shram.in"
    }

    # Check PM-Kisan
    pmkisan_eligible, pmkisan_reason, pmkisan_confidence = is_eligible_pm_kisan(
        age=age,
        is_farmer=is_farmer or False,
        land_holding_hectares=land_holding_hectares,
        is_government_employee=is_government_employee,
        previous_year_income=annual_income,
        occupation=occupation
    )

    results["PM-Kisan"] = {
        "eligible": pmkisan_eligible,
        "confidence": pmkisan_confidence,
        "reason": pmkisan_reason,
        "monthly_benefit": "₹2,000 (₹6,000/year in 3 installments)",
        "helpline": "1800-270-0888",
        "url": "pmkisan.gov.in"
    }

    # Ranking: eligible schemes first, then by confidence
    eligible_schemes = [s for s, r in results.items() if r["eligible"]]
    ineligible_schemes = [s for s, r in results.items() if not r["eligible"]]

    # Sort by confidence within each group
    eligible_schemes.sort(key=lambda s: results[s]["confidence"], reverse=True)
    ineligible_schemes.sort(key=lambda s: results[s]["confidence"], reverse=True)

    ranked = eligible_schemes + ineligible_schemes

    # Generate recommendation
    if eligible_schemes:
        if len(eligible_schemes) == 1:
            recommendation = f"You are eligible for {eligible_schemes[0]}. This scheme best matches your profile."
        else:
            recommendation = f"You are eligible for multiple schemes: {', '.join(eligible_schemes)}. Choose the one that best suits your needs."
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
