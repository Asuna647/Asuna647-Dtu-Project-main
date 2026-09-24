"""
OCR Service for Digital Saarthi

Handles document processing, Tesseract OCR with fallback for missing binary,
structured field extraction (Age, DOB, Name, Gender, BPL status), field-level confidence scoring,
PII redaction, and strict in-memory privacy lifecycle.
"""

import io
import re
import logging
from typing import Dict, Any, Optional, Tuple
from PIL import Image, ImageEnhance, ImageOps
import pytesseract

# Configure logging, explicitly avoid logging PII
logger = logging.getLogger(__name__)

CURRENT_YEAR = 2026


def preprocess_image(image_bytes: bytes) -> Image.Image:
    """
    Preprocess image bytes for OCR enhancement.
    - Loads image safely
    - Converts to Grayscale
    - Enhances contrast
    - Normalizes size if too small
    """
    if not image_bytes:
        raise ValueError("Invalid or corrupted image data: empty payload")

    try:
        # Load image
        img = Image.open(io.BytesIO(image_bytes))

        # Convert to Grayscale
        img = ImageOps.grayscale(img)

        # Enhance Contrast
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(2.0)

        # Scale up small images for better OCR resolution if needed
        w, h = img.size
        if w < 300 or h < 300:
            scale_factor = max(300 / w, 300 / h)
            img = img.resize((int(w * scale_factor), int(h * scale_factor)), Image.Resampling.LANCZOS)

        return img
    except Exception as e:
        logger.error(f"Failed to preprocess image: {e.__class__.__name__}")
        raise ValueError("Invalid or corrupted image data")


def extract_raw_text(image: Image.Image) -> str:
    """Run Tesseract OCR. Falls back to empty string if binary is missing or errors."""
    try:
        # Attempt multi-language OCR (English + Hindi)
        return pytesseract.image_to_string(image, lang='eng+hin')
    except pytesseract.TesseractNotFoundError:
        logger.warning("Tesseract binary not found on system PATH. OCR falling back to manual input.")
        return ""
    except Exception as e:
        logger.warning(f"Tesseract OCR execution error: {e.__class__.__name__}")
        return ""


def sanitize_pii(text: str) -> str:
    """
    Redacts sensitive PII from extracted text (Phase 34, 35).
    - Masks 12-digit Aadhaar numbers: 'XXXX-XXXX-XXXX'
    - Masks 16-digit Virtual IDs: 'XXXX-XXXX-XXXX-XXXX'
    """
    if not text:
        return ""

    # Redact 12-digit Aadhaar patterns (e.g., 1234 5678 9012 or 1234-5678-9012 or 123456789012)
    masked = re.sub(r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}\b', 'XXXX-XXXX-XXXX', text)

    # Redact 16-digit VID patterns
    masked = re.sub(r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b', 'XXXX-XXXX-XXXX-XXXX', masked)

    return masked


def parse_aadhaar_bpl_text(raw_text: str) -> Dict[str, Any]:
    """
    Extract structured fields using regex and heuristic rules (Phase 15, Phase 17).
    Extracts: Name, DOB, Age (calculated for 2026), Gender, BPL status.
    Computes per-field confidence and overall confidence.
    """
    extracted_name: Optional[str] = None
    extracted_dob: Optional[str] = None
    extracted_age: Optional[int] = None
    extracted_gender: Optional[str] = None
    has_bpl = False

    name_confidence = 0.0
    dob_confidence = 0.0
    age_confidence = 0.0
    gender_confidence = 0.0
    bpl_confidence = 0.0

    if not raw_text or not raw_text.strip():
        return {
            "name": None,
            "dob": None,
            "age": None,
            "gender": None,
            "has_bpl": False,
            "name_confidence": 0.0,
            "dob_confidence": 0.0,
            "age_confidence": 0.0,
            "gender_confidence": 0.0,
            "bpl_confidence": 0.0,
            "overall_confidence": 0.0,
        }

    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]

    # 1. DOB / Age Extraction
    # Pattern 1: Exact Date of Birth (DD/MM/YYYY or DD-MM-YYYY or DD.MM.YYYY)
    dob_full_match = re.search(
        r'(?:DOB|Date of Birth|जन्म तिथि|जन्म तारीख)[:\s]+([0-3]?\d[\/\-\.][0-1]?\d[\/\-\.](19\d{2}|20\d{2}))',
        raw_text,
        re.IGNORECASE
    )

    # Pattern 2: Year of Birth (YYYY)
    yob_match = re.search(
        r'(?:Year of Birth|YoB|DOB|Date of Birth|जन्म का वर्ष)[:\s]+(19\d{2}|20\d{2})',
        raw_text,
        re.IGNORECASE
    )

    # Pattern 3: Explicit Age (Age: XX)
    age_explicit_match = re.search(
        r'(?:Age|आयु|उम्र)[:\s]+(\d{1,3})',
        raw_text,
        re.IGNORECASE
    )

    if dob_full_match:
        extracted_dob = dob_full_match.group(1).replace('-', '/').replace('.', '/')
        birth_year = int(dob_full_match.group(2))
        calc_age = CURRENT_YEAR - birth_year
        if 0 <= calc_age <= 120:
            extracted_age = calc_age
            age_confidence = 0.95
            dob_confidence = 0.95
    elif yob_match:
        birth_year = int(yob_match.group(1))
        calc_age = CURRENT_YEAR - birth_year
        if 0 <= calc_age <= 120:
            extracted_age = calc_age
            extracted_dob = str(birth_year)
            age_confidence = 0.80
            dob_confidence = 0.75
    elif age_explicit_match:
        age_val = int(age_explicit_match.group(1))
        if 0 <= age_val <= 120:
            extracted_age = age_val
            age_confidence = 0.90

    # 2. Gender Extraction
    if re.search(r'\b(?:Female|महिला|स्त्री)\b', raw_text, re.IGNORECASE):
        extracted_gender = "Female"
        gender_confidence = 0.90
    elif re.search(r'\b(?:Male|पुरुष)\b', raw_text, re.IGNORECASE):
        extracted_gender = "Male"
        gender_confidence = 0.90
    elif re.search(r'\b(?:Transgender|किन्नर|अन्य)\b', raw_text, re.IGNORECASE):
        extracted_gender = "Transgender"
        gender_confidence = 0.85

    # 3. Name Extraction (Heuristic)
    # Filter out common boilerplate headers
    ignore_header_keywords = [
        "government", "india", "bharat", "aadhaar", "unique", "identification", "authority",
        "uidai", "enrollment", "help", "mera", "father", "husband", "address", "pension",
        "ration", "bpl", "male", "female", "dob", "year", "card", "department"
    ]

    for line in lines:
        line_clean = re.sub(r'[^a-zA-Z\s]', '', line).strip()
        words = line_clean.split()
        if 1 <= len(words) <= 4 and len(line_clean) >= 3:
            if not any(kw in line_clean.lower() for kw in ignore_header_keywords):
                # Candidate found
                extracted_name = line_clean
                name_confidence = 0.70
                break

    # 4. BPL / Ration Card Status Extraction
    explicit_bpl_keywords = ['bpl', 'below poverty line', 'antyodaya', 'aay', 'phh', 'गरीबी रेखा', 'बीपीएल']
    general_ration_keywords = ['ration card', 'खाद्य सुरक्षा', 'राशन कार्ड']

    raw_lower = raw_text.lower()
    if any(kw in raw_lower for kw in explicit_bpl_keywords):
        has_bpl = True
        bpl_confidence = 0.90
    elif any(kw in raw_lower for kw in general_ration_keywords):
        has_bpl = True
        bpl_confidence = 0.60
    else:
        has_bpl = False
        bpl_confidence = 0.0

    # 5. Calculate Overall Document Confidence
    confidences = [c for c in [age_confidence, dob_confidence, gender_confidence, name_confidence, bpl_confidence] if c > 0]
    if confidences:
        overall_confidence = round(sum(confidences) / max(len(confidences), 2), 2)
        overall_confidence = min(max(overall_confidence, 0.0), 1.0)
    else:
        overall_confidence = 0.0

    return {
        "name": extracted_name,
        "dob": extracted_dob,
        "age": extracted_age,
        "gender": extracted_gender,
        "has_bpl": has_bpl,
        "name_confidence": name_confidence,
        "dob_confidence": dob_confidence,
        "age_confidence": age_confidence,
        "gender_confidence": gender_confidence,
        "bpl_confidence": bpl_confidence,
        "overall_confidence": overall_confidence,
    }


def process_document_bytes(file_bytes: bytes, filename: str, content_type: str) -> Dict[str, Any]:
    """
    Main entry point for document OCR flow.
    Enforces in-memory processing (no persistent files on disk), PII sanitization, and error isolation.
    """
    try:
        # 1. Image Preprocessing
        img = preprocess_image(file_bytes)

        # 2. Extract Raw Text (with safe Tesseract fallback)
        raw_text = extract_raw_text(img)

        # 3. Structured Field Extraction & Confidence Scoring
        structured = parse_aadhaar_bpl_text(raw_text)

        # 4. PII Sanitization for safe client preview (truncate and mask Aadhaar numbers)
        sanitized_text = sanitize_pii(raw_text)[:500]

        return {
            "name": structured["name"],
            "age": structured["age"],
            "dob": structured["dob"],
            "gender": structured["gender"],
            "has_bpl": structured["has_bpl"],
            "confidence": structured["overall_confidence"],
            "field_confidences": {
                "name": structured["name_confidence"],
                "dob": structured["dob_confidence"],
                "age": structured["age_confidence"],
                "gender": structured["gender_confidence"],
                "has_bpl": structured["bpl_confidence"],
            },
            "raw_text": sanitized_text,
            "needs_confirmation": True,
        }
    except ValueError as e:
        raise
    except Exception as e:
        logger.error(f"Document processing failed unexpectedly: {e.__class__.__name__}")
        raise
