"""
Digital Saarthi API — FastAPI Backend

AI-powered Action-Guidance Layer for government services.
Target users: elderly, low-literacy users, caregivers.
"""

import logging
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import List

from app.models import (
    EligibilityCheckRequest,
    EligibilityResult,
    VoiceQueryRequest,
    VoiceQueryResponse,
    DocumentScanResponse,
    DocumentConfirmationRequest,
    HealthCheckResponse,
    SchemeResponse,
    SchemeSourceResponse,
    VoiceUploadResponse,
    IntentDetectionResponse,
)
from app.rule_engine import check_ignoaps
from app.knowledge_base import get_all_schemes, get_scheme_by_id
from app.retrieval import find_schemes
from app.ocr_service import process_document_bytes
from app.stt_service import transcribe_audio
from app.intent_engine import detect_intent

# ============================================================================
# APP INITIALIZATION
# ============================================================================

app = FastAPI(
    title="Digital Saarthi API",
    description="AI-powered Action-Guidance Layer for government services",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

logger = logging.getLogger(__name__)

# ============================================================================
# CONSTANTS
# ============================================================================

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "application/pdf"}

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _detect_intent(query: str) -> tuple[str, float]:
    """
    Lightweight keyword-based intent detection.
    Returns (intent, confidence) tuple.
    Does NOT use LLM — that's Stage 6.
    """
    query_lower = query.lower()

    # Pension-related keywords (Hindi + English)
    pension_keywords = ["pension", "vridha", "budha", "60", "pensioner", "retired"]
    kisan_keywords = ["kisan", "farm", "krishi", "agriculture", "farmer"]
    shram_keywords = ["shram", "labour", "majdoor", "worker", "unorganized"]

    # Scheme info keywords
    info_keywords = ["kya", "kaisa", "batao", "information", "info", "what", "how", "tell"]

    # Check for pension/scheme-specific intent first
    for kw in pension_keywords + kisan_keywords + shram_keywords:
        if kw in query_lower:
            return ("eligibility_check", 0.85)

    # Check for info-seeking intent
    for kw in info_keywords:
        if kw in query_lower:
            return ("scheme_info", 0.70)

    # Default fallback
    return ("unknown", 0.30)


def _scheme_to_response(scheme_dict: dict) -> SchemeResponse:
    """Convert a scheme dict to SchemeResponse Pydantic model."""
    return SchemeResponse(
        id=scheme_dict["id"],
        name=scheme_dict["name"],
        short_name=scheme_dict["short_name"],
        category=scheme_dict["category"],
        description=scheme_dict["description"],
        eligibility_criteria=scheme_dict["eligibility_criteria"],
        required_documents=scheme_dict["required_documents"],
        benefits=scheme_dict["benefits"],
        steps=scheme_dict["steps"],
        source=SchemeSourceResponse(**scheme_dict["source"]),
    )

# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.get("/", response_class=JSONResponse)
async def root():
    """Root endpoint — service identifier."""
    return {"message": "Digital Saarthi API - Action Guidance Layer"}


@app.get("/health", response_model=HealthCheckResponse)
async def health():
    """Health check endpoint."""
    return HealthCheckResponse()


@app.get("/api/schemes", response_model=List[SchemeResponse])
async def list_schemes():
    """
    List all schemes with full metadata.
    Returns complete scheme records including source verification.
    """
    schemes = get_all_schemes()
    return [_scheme_to_response(s) for s in schemes]


@app.get("/api/schemes/{scheme_id}", response_model=SchemeResponse)
async def get_scheme(scheme_id: str):
    """
    Get a single scheme by ID.
    Returns 404 if scheme not found.
    """
    scheme = get_scheme_by_id(scheme_id)
    if not scheme:
        raise HTTPException(status_code=404, detail="Scheme not found")
    return _scheme_to_response(scheme)


@app.post("/api/check-eligibility", response_model=EligibilityResult)
async def check_eligibility(request: EligibilityCheckRequest):
    """
    Check eligibility for a government scheme.
    Uses deterministic rule engine — no LLM.
    Routes to correct rule function based on scheme.
    """
    scheme = request.scheme.value

    if scheme == "IGNOAPS":
        return check_ignoaps(request.age, request.has_bpl)

    elif scheme == "ESHRAM":
        # Stage 9 implementation — return structured not_implemented
        return EligibilityResult(
            eligible=False,
            scheme="ESHRAM",
            verdict="not_implemented",
            reasons=[
                "✗ E-Shram eligibility check is not yet implemented.",
                "ℹ This feature will be available in the next update.",
            ],
            steps=[
                "Step 1: Visit https://eshram.gov.in for more information.",
                "Step 2: Register on the E-Shram portal for updates.",
            ],
            warning="E-Shram eligibility verification is under development.",
            confidence=0.0,
        )

    elif scheme == "PM_KISAN":
        # Stage 9 implementation — return structured not_implemented
        return EligibilityResult(
            eligible=False,
            scheme="PM_KISAN",
            verdict="not_implemented",
            reasons=[
                "✗ PM-Kisan eligibility check is not yet implemented.",
                "ℹ This feature will be available in the next update.",
            ],
            steps=[
                "Step 1: Visit https://pmkisan.gov.in for more information.",
                "Step 2: Check eligibility criteria on the official portal.",
            ],
            warning="PM-Kisan eligibility verification is under development.",
            confidence=0.0,
        )

    else:
        # This shouldn't happen due to Pydantic enum, but safety fallback
        return EligibilityResult(
            eligible=False,
            scheme=scheme,
            verdict="unknown_scheme",
            reasons=[f"✗ Unknown scheme: {scheme}"],
            steps=[],
            warning="Please select a valid scheme from the list.",
            confidence=0.0,
        )


@app.post("/api/voice-query", response_model=VoiceQueryResponse)
async def voice_query(request: VoiceQueryRequest):
    """
    Process voice/text query.
    Lightweight keyword matching + scheme retrieval.
    Does NOT use LLM — that's Stage 6.
    """
    query = request.query
    language = request.language

    # Detect intent
    intent, confidence = _detect_intent(query)

    # Find matching schemes
    matched = find_schemes(query)
    matched_responses = [_scheme_to_response(s) for s in matched]

    return VoiceQueryResponse(
        matched_schemes=matched_responses,
        intent=intent,
        confidence=confidence,
        original_query=query,
    )


@app.post("/api/scan-document", response_model=DocumentScanResponse)
async def scan_document(file: UploadFile = File(...)):
    """
    Process document image (OCR and structured extraction).
    Validates file type and size, extracts fields, and returns them for confirmation.
    """
    # Validate content type
    content_type = file.content_type or "application/octet-stream"
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported file type: {content_type}. Allowed: JPEG, PNG, PDF",
        )

    # Read file content for processing and size validation
    content = await file.read()
    file_size = len(content)

    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large: {file_size} bytes. Maximum allowed: {MAX_FILE_SIZE} bytes (10 MB)",
        )

    try:
        # Run OCR pipeline
        extraction_result = process_document_bytes(content, file.filename, content_type)

        warning_msg = None
        if extraction_result["confidence"] < 0.4:
            warning_msg = "Low OCR confidence or Tesseract absent. Please verify and edit extracted fields below."

        return DocumentScanResponse(
            name=extraction_result["name"],
            age=extraction_result["age"],
            dob=extraction_result["dob"],
            gender=extraction_result["gender"],
            has_bpl=extraction_result["has_bpl"],
            confidence=extraction_result["confidence"],
            field_confidences=extraction_result["field_confidences"],
            raw_text=extraction_result["raw_text"],
            needs_confirmation=extraction_result["needs_confirmation"],
            warning=warning_msg
        )
    except ValueError as e:
        raise HTTPException(
            status_code=422,
            detail="Corrupted or unreadable image file"
        )
    except Exception as e:
        # Fallback to prevent 500 error on unknown processing fault
        return DocumentScanResponse(
            confidence=0.0,
            needs_confirmation=True,
            warning="Document scanning failed or is unavailable. Please enter your details manually."
        )


@app.post("/api/confirm-document", response_model=EligibilityResult)
async def confirm_document(request: DocumentConfirmationRequest):
    """
    Endpoint for user-confirmed document fields.
    Passes confirmed values to the rule engine for policy evaluation.
    Enforces user-in-the-loop validation.
    """
    scheme = request.scheme.value

    if scheme == "IGNOAPS":
        return check_ignoaps(request.confirmed_age, request.confirmed_has_bpl)
    else:
        # Return structured not_implemented directly for others, as in check-eligibility
        return EligibilityResult(
            eligible=False,
            scheme=scheme,
            verdict="not_implemented",
            reasons=[
                f"✗ {scheme} eligibility check is not yet implemented.",
                "ℹ This feature will be available in the next update.",
            ],
            steps=[],
            warning=f"{scheme} eligibility verification is under development.",
            confidence=0.0,
        )


@app.post("/api/voice-upload", response_model=VoiceUploadResponse)
async def voice_upload(file: UploadFile = File(...), language_hint: str = "auto"):
    """
    Upload and process audio file for STT + intent detection + scheme matching.

    Validates audio file, transcribes to text, detects intent, and retrieves matching schemes.
    Returns full response with transcription, detected intent, and matched schemes.
    """
    # Validate file size
    content = await file.read()
    file_size = len(content)

    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail="Audio file exceeds 10 MB limit"
        )

    # Validate MIME type
    content_type = file.content_type or "application/octet-stream"
    allowed_audio_mimes = {"audio/wav", "audio/mpeg", "audio/mp4", "audio/x-flac", "audio/flac"}

    if content_type not in allowed_audio_mimes:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported audio format. Supported: wav, mp3, m4a, flac"
        )

    try:
        # Transcribe audio
        stt_result = transcribe_audio(content, language_hint)

        # Check for errors
        if "error" in stt_result:
            raise HTTPException(
                status_code=422,
                detail=stt_result["error"]
            )

        transcribed_text = stt_result.get("transcribed_text", "")
        detected_language = stt_result.get("detected_language", "unknown")
        stt_confidence = stt_result.get("stt_confidence", 0.0)
        duration = stt_result.get("duration_seconds", 0.0)
        processing_time = stt_result.get("processing_time_ms", 0)
        is_silent = stt_result.get("is_silent", False)
        stt_provider = stt_result.get("stt_provider", "unknown")

        # If silent, return 200 with is_silent=True (not an error)
        if is_silent:
            return VoiceUploadResponse(
                transcribed_text="",
                detected_language="unknown",
                stt_confidence=0.0,
                is_silent=True,
                duration_seconds=duration,
                processing_time_ms=processing_time,
                stt_provider=stt_provider,
                intent=None,
                matched_schemes=[],
            )

        # If no transcribed text, return with error flag
        if not transcribed_text:
            return VoiceUploadResponse(
                transcribed_text="",
                detected_language=detected_language,
                stt_confidence=0.0,
                is_silent=False,
                duration_seconds=duration,
                processing_time_ms=processing_time,
                stt_provider=stt_provider,
                intent=None,
                matched_schemes=[],
                error="Speech recognition service unavailable"
            )

        # Detect intent from transcribed text
        intent_result = detect_intent(transcribed_text, detected_language)

        # Find matched schemes
        matched_scheme_ids = intent_result.get("matched_schemes", [])
        matched_schemes = []
        for scheme_id in matched_scheme_ids:
            scheme = get_scheme_by_id(scheme_id)
            if scheme:
                matched_schemes.append(_scheme_to_response(scheme))

        # If no schemes matched via keywords, get all schemes (graceful degradation)
        if not matched_schemes:
            matched_schemes = [_scheme_to_response(s) for s in get_all_schemes()]

        # Build intent response
        intent_response = IntentDetectionResponse(
            intent=intent_result["intent"],
            confidence=intent_result["confidence"],
            matched_schemes=matched_scheme_ids,
            reasoning=intent_result.get("reasoning", ""),
            ambiguous=intent_result.get("ambiguous", False),
            top_alternatives=intent_result.get("top_alternatives", [])
        )

        return VoiceUploadResponse(
            transcribed_text=transcribed_text,
            detected_language=detected_language,
            stt_confidence=stt_confidence,
            is_silent=False,
            duration_seconds=duration,
            processing_time_ms=processing_time,
            stt_provider=stt_provider,
            intent=intent_response,
            matched_schemes=matched_schemes,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Voice upload processing failed: {e.__class__.__name__}")
        raise HTTPException(
            status_code=503,
            detail="Speech recognition service unavailable"
        )
