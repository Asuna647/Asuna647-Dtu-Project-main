"""
Digital Saarthi Knowledge Base — Verified Scheme Records

Each scheme record is typed and source-verified with official URLs,
departments, helplines, and last-verified dates. No invented facts.
"""

from typing import List, TypedDict, Optional


class SchemeSource(TypedDict):
    """Official source metadata for a government scheme."""
    official_url: str
    department: str
    helpline: Optional[str]
    last_verified: str  # ISO date string, e.g. "2026-09-24"


class SchemeRecord(TypedDict):
    """Complete typed scheme record."""
    id: str
    name: str
    short_name: str
    category: str  # "pension", "labour", "agriculture"
    description: str
    eligibility_criteria: List[str]
    required_documents: List[str]
    benefits: List[str]
    steps: List[str]
    source: SchemeSource


# ============================================================================
# SCHEME RECORDS — VERIFIED FACTS ONLY
# ============================================================================

IGNOAPS: SchemeRecord = {
    "id": "ignoaps",
    "name": "Indira Gandhi National Old Age Pension Scheme",
    "short_name": "IGNOAPS",
    "category": "pension",
    "description": (
        "A central government pension scheme for elderly citizens living below the poverty line. "
        "Provides monthly financial assistance to eligible senior citizens aged 60 and above."
    ),
    "eligibility_criteria": [
        "Age 60 years or above",
        "Below Poverty Line (BPL) status with valid BPL Ration Card",
        "Indian citizen",
        "Not receiving any other pension from government",
    ],
    "required_documents": [
        "Aadhaar Card or voter ID",
        "BPL Ration Card",
        "Bank passbook (for account details)",
        "Age proof (birth certificate or voter ID)",
    ],
    "benefits": [
        "Central contribution: ₹200–₹500/month (varies by age and state top-ups)",
        "State governments may provide additional amounts",
        "Transferred directly to bank account",
    ],
    "steps": [
        "Step 1: Visit your local Gram Panchayat, Ward Office, or Social Welfare Department office",
        "Step 2: Collect IGNOAPS application form (Form P-1)",
        "Step 3: Attach self-attested copies of Aadhaar, BPL card, bank passbook, and age proof",
        "Step 4: Submit the completed form with documents to the Social Welfare Officer",
        "Step 5: Collect your application receipt and track status online at https://nsap.nic.in",
    ],
    "source": {
        "official_url": "https://nsap.nic.in",
        "department": "Ministry of Rural Development, Government of India",
        "helpline": "14567",  # Elder helpline
        "last_verified": "2026-09-24",
    },
}

ESHRAM: SchemeRecord = {
    "id": "eshram",
    "name": "E-Shram: National Database of Unorganized Workers",
    "short_name": "E-Shram",
    "category": "labour",
    "description": (
        "A voluntary registration scheme for informal/unorganized workers. "
        "Provides access to government social security benefits, accident insurance, and pension schemes."
    ),
    "eligibility_criteria": [
        "Age 18–59 years",
        "Unorganized sector worker (not covered by EPFO or ESIC)",
        "Not a government employee",
        "Not a member of any other social security scheme",
    ],
    "required_documents": [
        "Aadhaar Card (or any ID for temporary registration)",
        "Mobile number (for OTP verification)",
        "Bank account details (optional but recommended)",
    ],
    "benefits": [
        "E-Shram card with unique identity number",
        "Access to Central government accident insurance (₹2 lakh coverage)",
        "Eligibility for various state and central government schemes",
        "Pension contribution credits (depending on other schemes)",
    ],
    "steps": [
        "Step 1: Visit the official E-Shram portal at https://eshram.gov.in",
        "Step 2: Click 'Register as a Worker' and verify your Aadhaar",
        "Step 3: Provide your occupation, workplace, and bank account details",
        "Step 4: Enter OTP sent to your registered mobile number",
        "Step 5: Download your E-Shram card from the portal",
    ],
    "source": {
        "official_url": "https://eshram.gov.in",
        "department": "Ministry of Labour & Employment, Government of India",
        "helpline": "14434",
        "last_verified": "2026-09-24",
    },
}

PM_KISAN: SchemeRecord = {
    "id": "pm_kisan",
    "name": "Pradhan Mantri Kisan Samman Nidhi Yojana",
    "short_name": "PM-Kisan",
    "category": "agriculture",
    "description": (
        "A central government scheme providing direct cash transfer to farmer families. "
        "Aims to support farmers' income and reduce their financial burden."
    ),
    "eligibility_criteria": [
        "Farmer family with cultivable landholding",
        "Landholding up to 2 hectares (5 acres)",
        "Indian citizen",
        "Not receiving income tax or government salary",
    ],
    "required_documents": [
        "Aadhaar Card",
        "Land ownership proof or lease deed",
        "Bank account details (preferably joint if joint ownership)",
        "Mobile number linked to Aadhaar",
    ],
    "benefits": [
        "₹6,000 per year in three equal instalments of ₹2,000",
        "Direct bank transfer (DBT) to registered account",
        "Automatically credited by government",
    ],
    "steps": [
        "Step 1: Visit https://pmkisan.gov.in or your nearest Common Service Centre (CSC)",
        "Step 2: Click 'Farmer Corner' → 'New Farmer Registration'",
        "Step 3: Enter your Aadhaar number, state, and district",
        "Step 4: Provide land details and bank account information",
        "Step 5: Submit and receive registration number for tracking",
    ],
    "source": {
        "official_url": "https://pmkisan.gov.in",
        "department": "Ministry of Agriculture & Farmers Welfare, Government of India",
        "helpline": "155261",
        "last_verified": "2026-09-24",
    },
}

# ============================================================================
# KNOWLEDGE BASE COLLECTION
# ============================================================================

SCHEMES_DB: List[SchemeRecord] = [IGNOAPS, ESHRAM, PM_KISAN]


def get_all_schemes() -> List[SchemeRecord]:
    """Return all schemes from the knowledge base."""
    return SCHEMES_DB


def get_scheme_by_id(scheme_id: str) -> Optional[SchemeRecord]:
    """
    Look up a scheme by its id field.
    Returns the scheme record or None if not found.
    """
    for scheme in SCHEMES_DB:
        if scheme["id"].lower() == scheme_id.lower():
            return scheme
    return None
