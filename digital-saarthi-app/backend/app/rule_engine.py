from typing import List, Optional, Tuple
from app.models import EligibilityResult
from app.scheme_rules import is_eligible_eshram, is_eligible_pm_kisan


IGNOAPS_STEPS = [
    "Step 1: Visit your local Gram Panchayat or Ward Office.",
    "Step 2: Obtain Form P-1 for IGNOAPS Old Age Pension.",
    "Step 3: Attach self-attested copies of Aadhaar, BPL Ration Card, and Bank Passbook.",
    "Step 4: Submit to the Social Welfare Officer and collect your application receipt."
]

IGNOAPS_BPL_STEPS = [
    "Step 1: Visit your nearest Tehsil/Block office or Common Service Centre (CSC).",
    "Step 2: Apply for a Below Poverty Line (BPL) Ration Card with your income proof.",
    "Step 3: After receiving the BPL card, return here to apply for IGNOAPS Pension."
]


def check_ignoaps(age: Optional[int], has_bpl: bool) -> EligibilityResult:
    """
    Evaluate IGNOAPS eligibility using official government rules.

    Rule: Senior citizens aged 60 years or above belonging to Below Poverty Line (BPL) households.
    Source URL: https://nsap.nic.in
    Verification Date: 2026-09-24
    Confidence Level: 1.0 (with complete data), 0.0 (with missing age)
    """
    # Rule as code comment:
    # IGNOAPS Rule: Senior citizens aged 60 years or above belonging to Below Poverty Line (BPL) households.
    # Source URL: https://nsap.nic.in
    # Verification Date: 2026-09-24
    # Confidence Level: 1.0
    reasons: List[str] = []

    # 1. Missing age -> CANNOT DETERMINE (Zero confidence, never guess)
    if age is None:
        return EligibilityResult(
            eligible=False,
            scheme="IGNOAPS",
            verdict="cannot_determine",
            reasons=["✗ Age missing or unreadable from document. Please scan a clear Aadhaar card."],
            steps=[],
            warning="Ensure the DOB/Age section of your Aadhaar card is clearly visible.",
            confidence=0.0
        )

    # 2. Out-of-range safety check
    if age < 0 or age > 120:
        return EligibilityResult(
            eligible=False,
            scheme="IGNOAPS",
            verdict="invalid_input",
            reasons=[f"✗ Invalid age provided: {age}. Age must be between 0 and 120."],
            steps=[],
            warning="Please check your document data and re-enter.",
            confidence=0.0
        )

    # 3. Rule evaluations
    age_eligible = age >= 60
    if age_eligible:
        reasons.append(f"✓ Age is {age} years — meets the minimum requirement of 60 years.")
    else:
        reasons.append(f"✗ Age is {age} years — minimum required age is 60 years.")

    if has_bpl:
        reasons.append("✓ BPL (Below Poverty Line) card status verified.")
    else:
        reasons.append("✗ BPL card status not verified — required for IGNOAPS.")

    eligible = age_eligible and has_bpl

    return EligibilityResult(
        eligible=eligible,
        scheme="IGNOAPS",
        verdict="Eligible for IGNOAPS Pension" if eligible else "Not currently eligible",
        reasons=reasons,
        steps=IGNOAPS_STEPS if eligible else (IGNOAPS_BPL_STEPS if not has_bpl else []),
        warning=None if eligible else "Do not pay any fees — government pension applications are completely free.",
        confidence=1.0
    )


def check_eshram(
    age: Optional[int] = None,
    annual_income: Optional[int] = None,
    is_organised_worker: bool = False,
    has_esic_coverage: bool = False,
    has_epf_coverage: bool = False,
    is_income_tax_payee: bool = False,
    occupation: Optional[str] = None
) -> Tuple[bool, str, float]:
    """
    Rule Engine entry point for E-Shram eligibility determination.

    Rule: Unorganized worker aged 16-59 years, not covered under EPFO/ESIC, not an income tax payee.
    Source URL: https://eshram.gov.in/faqs
    Verification Date: 2026-09-24
    Confidence Level: 1.0
    """
    # Rule as code comment:
    # E-Shram Rule: Workers in the unorganised sector aged 16 to 59 years without ESIC/EPF or Income Tax payee status.
    # Source URL: https://eshram.gov.in/faqs
    # Verification Date: 2026-09-24
    # Confidence Level: 1.0
    return is_eligible_eshram(
        age=age,
        annual_income=annual_income,
        is_organised_worker=is_organised_worker,
        has_esic_coverage=has_esic_coverage,
        has_epf_coverage=has_epf_coverage,
        is_income_tax_payee=is_income_tax_payee,
        occupation=occupation
    )


def check_pm_kisan(
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
    Rule Engine entry point for PM-Kisan eligibility determination.

    Rule: All landholding farmer families with cultivable land (>0 ha) are eligible, subject to exclusion categories.
    Source URL: https://www.pmkisan.gov.in/
    Verification Date: 2026-09-24
    Confidence Level: 1.0
    """
    # Rule as code comment:
    # PM-Kisan Rule: All landholding farmer families with cultivable land (>0 ha) excluding institutional landholders, govt employees (except Class IV), income tax payees, high pensioners, and professionals.
    # Source URL: https://www.pmkisan.gov.in/
    # Verification Date: 2026-09-24
    # Confidence Level: 1.0
    return is_eligible_pm_kisan(
        age=age,
        is_farmer=is_farmer,
        land_holding_hectares=land_holding_hectares,
        is_government_employee=is_government_employee,
        is_class_iv_employee=is_class_iv_employee,
        is_income_tax_payee=is_income_tax_payee,
        monthly_pension=monthly_pension,
        is_institutional_landholder=is_institutional_landholder,
        is_registered_professional=is_registered_professional,
        previous_year_income=previous_year_income,
        occupation=occupation
    )
