from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Any
from enum import Enum


class SchemeType(str, Enum):
    IGNOAPS = "IGNOAPS"
    ESHRAM = "ESHRAM"
    PM_KISAN = "PM_KISAN"


# === REQUEST MODELS ===

class EligibilityCheckRequest(BaseModel):
    scheme: SchemeType = Field(..., description="Target scheme identifier")
    age: Optional[int] = Field(None, ge=0, le=120, description="Age in years (0-120)")
    has_bpl: bool = Field(False, description="Possesses Below Poverty Line card")
    is_organised_worker: bool = Field(False, description="EPFO/ESIC covered worker")
    is_farmer: bool = Field(False, description="Owns cultivable land")

    @field_validator("age")
    @classmethod
    def validate_age_range(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and (v < 0 or v > 120):
            raise ValueError("Age must be between 0 and 120")
        return v


class VoiceQueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500, description="User query text or speech transcript")
    language: str = Field("hi-IN", description="Language locale tag")


class FieldConfidence(BaseModel):
    value: Optional[str] = None
    confidence: float = Field(0.0, ge=0.0, le=1.0)


class DocumentScanResponse(BaseModel):
    name: Optional[str] = None
    age: Optional[int] = None
    dob: Optional[str] = None
    gender: Optional[str] = None
    has_bpl: bool = False
    confidence: float = Field(0.0, ge=0.0, le=1.0, description="Overall document scan confidence")
    field_confidences: Optional[dict] = Field(default_factory=dict, description="Per-field confidence scores")
    raw_text: str = Field("", description="Sanitized extracted text (PII redacted/truncated)")
    needs_confirmation: bool = Field(True, description="Flag signaling frontend to prompt user confirmation")
    warning: Optional[str] = None


class DocumentConfirmationRequest(BaseModel):
    """Payload sent by frontend when user confirms or edits OCR-extracted fields."""
    scheme: SchemeType = Field(SchemeType.IGNOAPS, description="Target scheme identifier")
    confirmed_age: Optional[int] = Field(None, ge=0, le=120)
    confirmed_has_bpl: bool = Field(False)
    document_type: Optional[str] = Field("Aadhaar", description="Type of document scanned")


# === RESPONSE MODELS ===

class EligibilityResult(BaseModel):
    eligible: bool = Field(..., description="Overall eligibility determination")
    scheme: str = Field(..., description="Name of evaluated scheme")
    verdict: str = Field(..., description="User-facing verdict title")
    reasons: List[str] = Field(default_factory=list, description="Detailed decision factors")
    steps: List[str] = Field(default_factory=list, description="Numbered next action steps")
    warning: Optional[str] = Field(None, description="Cautionary advice or scam warnings")
    confidence: float = Field(1.0, ge=0.0, le=1.0, description="Confidence score of verdict")


class HealthCheckResponse(BaseModel):
    status: str = Field("healthy", description="API health status")
    service: str = Field("Digital Saarthi API", description="Service identifier")
    version: str = Field("1.0.0", description="API version")


# === SOURCE AND SCHEME RESPONSE MODELS ===

class SchemeSourceResponse(BaseModel):
    official_url: str = Field(..., description="Official government URL")
    department: str = Field(..., description="Issuing ministry/department name")
    helpline: Optional[str] = Field(None, description="National helpline number")
    last_verified: str = Field(..., description="ISO date when last verified")


class SchemeResponse(BaseModel):
    id: str = Field(..., description="Unique scheme identifier")
    name: str = Field(..., description="Full official scheme name")
    short_name: str = Field(..., description="Short display name")
    category: str = Field(..., description="Scheme category: pension, labour, agriculture")
    description: str = Field(..., description="Brief accessible description")
    eligibility_criteria: List[str] = Field(default_factory=list, description="Eligibility bullet points")
    required_documents: List[str] = Field(default_factory=list, description="Required documents")
    benefits: List[str] = Field(default_factory=list, description="Benefits provided")
    steps: List[str] = Field(default_factory=list, description="Numbered application steps")
    source: SchemeSourceResponse = Field(..., description="Source verification metadata")


class IntentDetectionResponse(BaseModel):
    intent: str = Field(..., description="eligibility_check|scheme_info|application_help|general|unknown")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Intent confidence (0.0-1.0)")
    matched_schemes: List[str] = Field(default_factory=list, description="Scheme IDs matching this intent")
    reasoning: str = Field("", description="Human-readable explanation of intent detection")
    ambiguous: bool = Field(False, description="True if top 2 intents within ±0.05 confidence")
    top_alternatives: List[Dict] = Field(default_factory=list, description="Alternative intents if ambiguous")


class VoiceUploadResponse(BaseModel):
    transcribed_text: str = Field(..., description="Transcribed audio text")
    detected_language: str = Field(..., description="Detected language: 'en', 'hi', 'mixed', 'unknown'")
    stt_confidence: float = Field(..., ge=0.0, le=1.0, description="STT confidence (0.0-1.0)")
    is_silent: bool = Field(False, description="Flag if audio was detected as silent")
    duration_seconds: float = Field(..., description="Audio duration in seconds")
    processing_time_ms: int = Field(..., description="Processing time in milliseconds")
    stt_provider: str = Field("openai_whisper", description="STT provider used: openai_whisper or speech_recognition")
    intent: Optional[IntentDetectionResponse] = Field(None, description="Detected intent if transcription succeeded")
    matched_schemes: List[SchemeResponse] = Field(default_factory=list, description="Schemes matching the detected intent")
    error: Optional[str] = Field(None, description="Error message if processing failed")


class VoiceQueryResponse(BaseModel):
    matched_schemes: List[SchemeResponse] = Field(default_factory=list, description="Schemes matching the query")
    intent: str = Field(..., description="Detected intent: eligibility_check, scheme_info, application_help, general, unknown")
    confidence: float = Field(0.0, ge=0.0, le=1.0, description="Intent confidence (0.0-1.0)")
    original_query: str = Field(..., description="Original query text preserved for reference")
