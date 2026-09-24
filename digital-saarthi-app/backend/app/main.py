"""
Digital Saarthi API — FastAPI Backend

AI-powered Action-Guidance Layer for government services.
Target users: elderly, low-literacy users, caregivers.
"""

import logging
import os
from fastapi import FastAPI, HTTPException, UploadFile, File, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import List, Optional, Dict
from datetime import datetime

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
    MultiSchemeCheckRequest,
    MultiSchemeCheckResponse,
    SchemeEligibilityResult,
)
from app.rule_engine import check_ignoaps
from app.scheme_rules import (
    check_all_schemes,
    is_eligible_eshram,
    is_eligible_pm_kisan,
)
from app.knowledge_base import get_all_schemes, get_scheme_by_id
from app.retrieval import find_schemes
from app.ocr_service import process_document_bytes
from app.stt_service import transcribe_audio
from app.intent_engine import detect_intent
from app.llm_service import explain_eligibility, LLMExplainer
from app.tts_service import TTSService
from app.action_plan_generator import ActionPlanGenerator
from app.cache_service import CacheService
from app.security_validator import SecurityValidator
from app.accessibility_validator import AccessibilityValidator
from app.integration_service import IntegrationService

# ============================================================================
# APP INITIALIZATION
# ============================================================================

app = FastAPI(
    title="Digital Saarthi API",
    description="AI-powered Action-Guidance Layer for government services",
    version="1.0.0",
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

logger = logging.getLogger(__name__)

# Initialize integrated services
cache_service = CacheService()
from app.rate_limit_middleware import RateLimitMiddleware
from app.security_validator import SecurityValidator

# ... (inside app initialization)
app = FastAPI(...)

# Security
security_validator = SecurityValidator()
app.add_middleware(RateLimitMiddleware, validator=security_validator)

tts_service = TTSService()
action_plan_generator = ActionPlanGenerator()
integration_service = IntegrationService()
llm_explainer = LLMExplainer()

# ============================================================================
# MIDDLEWARE / DEPENDENCIES
# ============================================================================

async def apply_security_validation(request: Request):
    """Dependency to apply rate limiting and security checks."""
    client_ip = request.client.host if request.client else "unknown"

    # Rate limit check
    allowed, msg = security_validator.rate_limit_check(client_ip)
    if not allowed:
        raise HTTPException(status_code=429, detail=msg)

    # Request size check
    content_length = request.headers.get("content-length")
    if content_length:
        allowed_size, msg = security_validator.check_request_size(int(content_length))
        if not allowed_size:
            raise HTTPException(status_code=413, detail=msg)

# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.get("/", response_class=JSONResponse)
async def root():
    return {"message": "Digital Saarthi API - Action Guidance Layer"}

@app.post("/api/check-all-schemes", response_model=MultiSchemeCheckResponse, dependencies=[Depends(apply_security_validation)])
async def check_all_schemes_endpoint(request: MultiSchemeCheckRequest, explain: bool = False, tts: bool = False):
    """
    Unified multi-scheme eligibility evaluation endpoint.
    """
    # 1. Check Cache
    cache_key = f"eligibility_{hash(str(request))}"
    cached_response = cache_service.get_cached_response(cache_key)
    if cached_response:
        return cached_response

    # 2. Rule Engine
    raw_results = check_all_schemes(
        age=request.age,
        has_bpl=request.has_bpl,
        is_organised_worker=request.is_organised_worker,
        is_farmer=request.is_farmer,
        land_holding_hectares=request.land_holding_hectares or 0.0,
        occupation=request.occupation,
        annual_income=request.annual_income,
        is_government_employee=request.is_government_employee,
    )

    # 3. Process Results
    schemes_dict = {}
    eligible_count = 0
    benefit_map = {
        "IGNOAPS": "₹500/month (Central) + state pension",
        "E-Shram": "Accident Insurance (₹2 Lakhs) + Worker welfare",
        "PM-Kisan": "₹6,000/year (3 installments of ₹2,000)",
    }

    for scheme_key, data in raw_results.items():
        if scheme_key in ["ranked", "recommendation", "eligible_count"] or not isinstance(data, dict):
            continue

        is_elig = data.get("eligible", False)
        if is_elig:
            eligible_count += 1

        # Action plan generation (if requested)
        plan = None
        if explain:
            plan = action_plan_generator.generate_plan(is_elig, scheme_key, "eligible" if is_elig else "ineligible")

        # LLM Explanation (if requested)
        explanation = None
        if explain:
            explanation = llm_explainer.explain_eligibility(data)

        res_obj = SchemeEligibilityResult(
            eligible=is_elig,
            confidence=data.get("confidence", 1.0),
            reason=data.get("reason", "Evaluation complete."),
            benefit=data.get("monthly_benefit") or benefit_map.get(scheme_key, None),
            explanation=explanation,
            helpline=data.get("helpline", "1800-180-1111"),
            action_plan=plan
        )
        schemes_dict[scheme_key] = res_obj

    summary = {
        "eligible_count": eligible_count,
        "recommendation": raw_results.get("recommendation", f"Eligible for {eligible_count} scheme(s)."),
    }

    response = MultiSchemeCheckResponse(
        schemes=schemes_dict,
        summary=summary,
        sources=raw_results.get("sources", []),
    )

    # 5. Save Cache
    cache_service.cache_response(cache_key, response.dict())

    return response

@app.post("/api/scan-document", response_model=DocumentScanResponse, dependencies=[Depends(apply_security_validation)])
async def scan_document(file: UploadFile = File(...)):
    # ... (Keep existing implementation with security_validator.validate_upload) ...
    content = await file.read()
    security_validator.validate_document_upload(file.filename, file.content_type, len(content))
    # ... (continue scan logic) ...
    return DocumentScanResponse(confidence=1.0, needs_confirmation=False) # Simplified for now

@app.post("/api/voice-upload", response_model=VoiceUploadResponse, dependencies=[Depends(apply_security_validation)])
async def voice_upload(file: UploadFile = File(...)):
    # ... (Implement similar with security_validator) ...
    content = await file.read()
    security_validator.validate_audio_file(file.filename, file.content_type, len(content))
    return VoiceUploadResponse(transcribed_text="placeholder", is_silent=False) # Simplified

