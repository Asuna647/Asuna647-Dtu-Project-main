"""
Digital Saarthi API Integration Tests

Uses FastAPI TestClient to test all documented endpoints.
Covers:
- All HTTP methods
- Pydantic response validation
- Error handling (404, 413, 422)
- Stub responses for Stage 2
- Intent detection and scheme retrieval
"""

import pytest
import io
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


# ============================================================================
# BASIC ENDPOINTS
# ============================================================================

def test_root():
    """GET / should return service identifier."""
    response = client.get("/")
    assert response.status_code == 200
    assert "Digital Saarthi" in response.json()["message"]


def test_health():
    """GET /health should return healthy status."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "Digital Saarthi API"
    assert data["version"] == "1.0.0"


# ============================================================================
# SCHEME ENDPOINTS
# ============================================================================

def test_list_schemes():
    """GET /api/schemes should return all three schemes."""
    response = client.get("/api/schemes")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 3

    # Check each scheme has required fields
    for scheme in data:
        assert "id" in scheme
        assert "name" in scheme
        assert "source" in scheme

    # Find IGNOAPS and check official URL
    ignoaps = next(s for s in data if s["id"] == "ignoaps")
    assert "nsap.nic.in" in ignoaps["source"]["official_url"]


def test_get_scheme_valid():
    """GET /api/schemes/ignoaps should return IGNOAPS scheme."""
    response = client.get("/api/schemes/ignoaps")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "ignoaps"
    assert data["short_name"] == "IGNOAPS"
    assert data["source"]["last_verified"] is not None


def test_get_scheme_nonexistent():
    """GET /api/schemes/nonexistent should return 404."""
    response = client.get("/api/schemes/nonexistent")
    assert response.status_code == 404
    data = response.json()
    assert data["detail"] == "Scheme not found"


# ============================================================================
# ELIGIBILITY CHECK ENDPOINT
# ============================================================================

def test_check_eligibility_ignoaps_eligible():
    """POST /api/check-eligibility (IGNOAPS, eligible)."""
    payload = {
        "scheme": "IGNOAPS",
        "age": 72,
        "has_bpl": True,
        "is_organised_worker": False,
        "is_farmer": False,
    }
    response = client.post("/api/check-eligibility", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["eligible"] is True
    assert data["confidence"] == 1.0


def test_check_eligibility_ignoaps_not_eligible_age():
    """POST /api/check-eligibility (IGNOAPS, age 59)."""
    payload = {
        "scheme": "IGNOAPS",
        "age": 59,
        "has_bpl": True,
        "is_organised_worker": False,
        "is_farmer": False,
    }
    response = client.post("/api/check-eligibility", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["eligible"] is False
    assert data["confidence"] == 1.0


def test_check_eligibility_ignoaps_cannot_determine():
    """POST /api/check-eligibility (IGNOAPS, age null)."""
    payload = {
        "scheme": "IGNOAPS",
        "age": None,
        "has_bpl": False,
        "is_organised_worker": False,
        "is_farmer": False,
    }
    response = client.post("/api/check-eligibility", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["eligible"] is False
    assert data["verdict"] == "cannot_determine"
    assert data["confidence"] == 0.0


def test_check_eligibility_eshram_not_implemented():
    """POST /api/check-eligibility (ESHRAM) returns not_implemented, not 500."""
    payload = {
        "scheme": "ESHRAM",
        "age": 35,
        "has_bpl": False,
        "is_organised_worker": False,
        "is_farmer": False,
    }
    response = client.post("/api/check-eligibility", json=payload)
    assert response.status_code == 200  # NOT 500
    data = response.json()
    assert data["eligible"] is False
    assert data["verdict"] == "not_implemented"
    assert data["confidence"] == 0.0


def test_check_eligibility_pm_kisan_not_implemented():
    """POST /api/check-eligibility (PM_KISAN) returns not_implemented, not 500."""
    payload = {
        "scheme": "PM_KISAN",
        "age": 45,
        "has_bpl": False,
        "is_organised_worker": False,
        "is_farmer": True,
    }
    response = client.post("/api/check-eligibility", json=payload)
    assert response.status_code == 200  # NOT 500
    data = response.json()
    assert data["eligible"] is False
    assert data["verdict"] == "not_implemented"
    assert data["confidence"] == 0.0


# ============================================================================
# VOICE QUERY ENDPOINT
# ============================================================================

def test_voice_query_pension_hindi():
    """POST /api/voice-query with Hindi pension keywords."""
    payload = {
        "query": "meri maa ko pension chahiye",
        "language": "hi-IN",
    }
    response = client.post("/api/voice-query", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert len(data["matched_schemes"]) > 0
    assert data["intent"] == "eligibility_check"
    assert data["confidence"] >= 0.0 and data["confidence"] <= 1.0
    assert data["original_query"] == "meri maa ko pension chahiye"


def test_voice_query_generic():
    """POST /api/voice-query with generic query (graceful degradation)."""
    payload = {
        "query": "government help",
        "language": "en-IN",
    }
    response = client.post("/api/voice-query", json=payload)
    assert response.status_code == 200
    data = response.json()
    # Should have at least 1 matched scheme (graceful degradation)
    assert len(data["matched_schemes"]) >= 1
    assert data["intent"] in ["eligibility_check", "scheme_info", "general", "unknown"]


def test_voice_query_empty_query():
    """POST /api/voice-query with empty query should return 422 (validation error)."""
    payload = {
        "query": "",
        "language": "en-IN",
    }
    response = client.post("/api/voice-query", json=payload)
    assert response.status_code == 422  # Validation error due to min_length=1


# ============================================================================
# DOCUMENT SCAN & CONFIRMATION ENDPOINTS
# ============================================================================

def test_scan_document_valid_image():
    """POST /api/scan-document with small synthetic PNG."""
    # Create valid synthetic image
    from PIL import Image
    img = Image.new("RGB", (100, 100), color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    png_bytes = buffer.getvalue()

    files = {"file": ("test.png", io.BytesIO(png_bytes), "image/png")}
    response = client.post("/api/scan-document", files=files)
    assert response.status_code == 200
    data = response.json()
    assert "confidence" in data
    assert "field_confidences" in data
    assert data["needs_confirmation"] is True


def test_confirm_document_eligible():
    """POST /api/confirm-document with confirmed valid data."""
    payload = {
        "scheme": "IGNOAPS",
        "confirmed_age": 65,
        "confirmed_has_bpl": True,
        "document_type": "Aadhaar"
    }
    response = client.post("/api/confirm-document", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["eligible"] is True
    assert data["confidence"] == 1.0


def test_scan_document_invalid_file_type():
    """POST /api/scan-document with text file should return 422."""
    text_bytes = b"This is a text file, not an image"
    files = {"file": ("test.txt", io.BytesIO(text_bytes), "text/plain")}
    response = client.post("/api/scan-document", files=files)
    assert response.status_code == 422
    data = response.json()
    assert "Unsupported file type" in data["detail"]


def test_scan_document_large_file():
    """POST /api/scan-document with >10 MB should return 413."""
    # Create a 11 MB byte array
    large_bytes = b"\x89PNG\r\n\x1a\n" + b"X" * (11 * 1024 * 1024)
    files = {"file": ("large.png", io.BytesIO(large_bytes), "image/png")}
    response = client.post("/api/scan-document", files=files)
    assert response.status_code == 413
    data = response.json()
    assert "File too large" in data["detail"]


def test_scan_document_pdf_stub():
    """POST /api/scan-document with stub PDF bytes should return 422 since Pillow cannot read it as an image."""
    pdf_bytes = b"%PDF-1.4\n" + b"0 0 obj\nendobj\n" + b"%%EOF"
    files = {"file": ("test.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    response = client.post("/api/scan-document", files=files)
    assert response.status_code == 422
    data = response.json()
    assert "Corrupted or unreadable image file" in data["detail"]


# ============================================================================
# ERROR HANDLING (Request Validation)
# ============================================================================

def test_check_eligibility_missing_scheme():
    """POST /api/check-eligibility without scheme should return 422."""
    payload = {
        "age": 72,
        "has_bpl": True,
    }
    response = client.post("/api/check-eligibility", json=payload)
    assert response.status_code == 422  # Validation error


def test_check_eligibility_invalid_age_range():
    """POST /api/check-eligibility with age 200 should return 422."""
    payload = {
        "scheme": "IGNOAPS",
        "age": 200,
        "has_bpl": True,
    }
    response = client.post("/api/check-eligibility", json=payload)
    assert response.status_code == 422


def test_voice_query_too_long():
    """POST /api/voice-query with query >500 chars should return 422."""
    payload = {
        "query": "A" * 501,
        "language": "en-IN",
    }
    response = client.post("/api/voice-query", json=payload)
    assert response.status_code == 422


def test_voice_query_missing_query():
    """POST /api/voice-query without query field should return 422."""
    payload = {
        "language": "en-IN",
    }
    response = client.post("/api/voice-query", json=payload)
    assert response.status_code == 422


# ============================================================================
# VOICE UPLOAD ENDPOINT (Stage 4)
# ============================================================================

def test_voice_upload_valid_audio_file():
    """POST /api/voice-upload with valid audio file (STT backends optional)."""
    import wave

    # Create a valid WAV file
    wav_buffer = io.BytesIO()
    with wave.open(wav_buffer, 'wb') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(16000)
        wav_file.writeframes(b'\x00\x00' * 16000)  # 1 second of silence

    wav_bytes = wav_buffer.getvalue()

    files = {"file": ("test.wav", io.BytesIO(wav_bytes), "audio/wav")}
    response = client.post("/api/voice-upload?language_hint=auto", files=files)

    # Should return 200 or 422 (depending on STT backend availability)
    # Accept both since SpeechRecognition/Whisper may not be configured
    assert response.status_code in [200, 422]


def test_voice_upload_invalid_mime_type():
    """POST /api/voice-upload with non-audio MIME type should return 422."""
    text_bytes = b"This is not audio"
    files = {"file": ("test.txt", io.BytesIO(text_bytes), "text/plain")}
    response = client.post("/api/voice-upload", files=files)

    assert response.status_code == 422
    data = response.json()
    assert "Unsupported audio format" in data["detail"]


def test_voice_upload_file_exceeds_10mb():
    """POST /api/voice-upload with file >10 MB should return 413."""
    # Create a large byte array (11 MB)
    large_bytes = b"RIFF" + b"\x00" * (11 * 1024 * 1024)
    files = {"file": ("large.wav", io.BytesIO(large_bytes), "audio/wav")}
    response = client.post("/api/voice-upload", files=files)

    assert response.status_code == 413
    data = response.json()
    assert "exceeds 10 MB" in data["detail"]


def test_voice_upload_corrupted_audio():
    """POST /api/voice-upload with corrupted audio should return 422."""
    corrupted_bytes = b"XXXX" + b"\x00" * 100  # Bad magic bytes
    files = {"file": ("bad.wav", io.BytesIO(corrupted_bytes), "audio/wav")}
    response = client.post("/api/voice-upload", files=files)

    assert response.status_code == 422


def test_voice_upload_response_schema():
    """Response should have all required fields for voice upload (if STT available)."""
    import wave

    wav_buffer = io.BytesIO()
    with wave.open(wav_buffer, 'wb') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(16000)
        wav_file.writeframes(b'\x00\x00' * 16000)

    wav_bytes = wav_buffer.getvalue()
    files = {"file": ("test.wav", io.BytesIO(wav_bytes), "audio/wav")}
    response = client.post("/api/voice-upload?language_hint=auto", files=files)

    # Accept both 200 and 422 (STT backend optional)
    assert response.status_code in [200, 422]

    if response.status_code == 200:
        data = response.json()
        # Required fields from VoiceUploadResponse
        assert "transcribed_text" in data
        assert "detected_language" in data
        assert "stt_confidence" in data
        assert isinstance(data["stt_confidence"], (int, float))
        assert 0.0 <= data["stt_confidence"] <= 1.0
