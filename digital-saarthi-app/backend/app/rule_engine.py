from typing import List, Optional
from app.models import EligibilityResult


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
