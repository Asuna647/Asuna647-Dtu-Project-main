import pytest
from pydantic import ValidationError
from app.models import (
    SchemeType,
    EligibilityCheckRequest,
    VoiceQueryRequest,
    DocumentScanResponse,
    EligibilityResult,
    HealthCheckResponse
)

def test_eligibility_check_request_valid():
    req = EligibilityCheckRequest(scheme=SchemeType.IGNOAPS, age=65, has_bpl=True)
    assert req.scheme == SchemeType.IGNOAPS
    assert req.age == 65
    assert req.has_bpl is True

def test_eligibility_check_request_invalid_age():
    # Age below 0
    with pytest.raises(ValidationError):
        EligibilityCheckRequest(scheme=SchemeType.IGNOAPS, age=-5, has_bpl=True)

    # Age above 120
    with pytest.raises(ValidationError):
        EligibilityCheckRequest(scheme=SchemeType.IGNOAPS, age=125, has_bpl=True)

def test_voice_query_request_validation():
    req = VoiceQueryRequest(query="मुझे पेंशन योजना के बारे में बताएं", language="hi-IN")
    assert req.query is not None
    assert req.language == "hi-IN"

    # Empty query validation
    with pytest.raises(ValidationError):
        VoiceQueryRequest(query="", language="hi-IN")

def test_document_scan_response_defaults():
    doc = DocumentScanResponse(raw_text="Aadhaar card sample")
    assert doc.age is None
    assert doc.has_bpl is False
    assert doc.confidence == 0.0
    assert doc.raw_text == "Aadhaar card sample"

def test_eligibility_result_structure():
    res = EligibilityResult(
        eligible=True,
        scheme="IGNOAPS",
        verdict="Eligible for IGNOAPS Pension",
        reasons=["✓ Age meets requirement"],
        steps=["Step 1: Visit Gram Panchayat"],
        warning=None,
        confidence=1.0
    )
    assert res.eligible is True
    assert res.confidence == 1.0
    assert len(res.steps) == 1

def test_health_check_response():
    health = HealthCheckResponse()
    assert health.status == "healthy"
    assert health.service == "Digital Saarthi API"
    assert health.version == "1.0.0"
