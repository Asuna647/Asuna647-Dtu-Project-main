"""
Tests for OCR Service and Image Processing Pipeline
"""

import io
import pytest
from PIL import Image
from app.ocr_service import preprocess_image, parse_aadhaar_bpl_text, process_document_bytes


def create_dummy_image(format="JPEG") -> bytes:
    """Helper to create dummy in-memory image bytes."""
    img = Image.new("RGB", (100, 100), color="white")
    buffer = io.BytesIO()
    img.save(buffer, format=format)
    return buffer.getvalue()


def test_preprocess_image_valid_jpeg():
    """Test loading and preprocessing a valid JPEG byte stream."""
    img_bytes = create_dummy_image(format="JPEG")
    processed_img = preprocess_image(img_bytes)
    assert processed_img is not None
    assert processed_img.mode == "L"  # Grayscale


def test_preprocess_image_corrupted_bytes():
    """Corrupted/random bytes should raise a ValueError."""
    corrupted_bytes = b"garbage_non_image_data_here"
    with pytest.raises(ValueError, match="Invalid or corrupted image data"):
        preprocess_image(corrupted_bytes)


def test_parse_aadhaar_bpl_text_age_extraction():
    """Extracts age from text containing Year of Birth or DOB."""
    text = "Government of India \n DOB: 1964 \n Gender: Female"
    result = parse_aadhaar_bpl_text(text)
    assert result["age"] == 62  # 2026 - 1964
    assert result["age_confidence"] > 0.5


def test_parse_aadhaar_bpl_text_bpl_card():
    """Extracts BPL status when keywords are present."""
    text = "BPL RATION CARD NO: 12345 STATE OF DELHI"
    result = parse_aadhaar_bpl_text(text)
    assert result["has_bpl"] is True
    assert result["bpl_confidence"] > 0.8


def test_parse_aadhaar_bpl_text_missing_data():
    """Returns low/zero confidence when text has no useful info."""
    text = "Unreadable blurred document text sample with no fields"
    result = parse_aadhaar_bpl_text(text)
    assert result["age"] is None
    assert result["has_bpl"] is False
    assert result["overall_confidence"] == 0.0


def test_process_document_bytes_memory_only():
    """Verifies that running the pipeline works with pure in-memory buffers."""
    img_bytes = create_dummy_image(format="PNG")
    result = process_document_bytes(img_bytes, "test.png", "image/png")
    assert "confidence" in result
    assert result["needs_confirmation"] is True


def test_privacy_temp_file_cleanup():
    """Verify processing stays memory-bound or cleans up (we do memory-bound via BytesIO)."""
    import os
    initial_files = set(os.listdir("."))

    img_bytes = create_dummy_image(format="PNG")
    process_document_bytes(img_bytes, "test_privacy.png", "image/png")

    final_files = set(os.listdir("."))
    # Ensure no new temporary image files were leaked into CWD
    new_files = final_files - initial_files
    assert not any(f.endswith(".png") or f.endswith(".jpg") for f in new_files)


def test_no_pii_in_logs(caplog):
    """Ensure logger does not output PII like exact extracted text when failing."""
    import logging
    caplog.set_level(logging.WARNING)
    img_bytes = create_dummy_image(format="PNG")
    # This will trigger the OCR fallback warning if Tesseract is missing
    process_document_bytes(img_bytes, "test.png", "image/png")

    # Verify no PII fields show up in logs (just generic messages)
    for record in caplog.records:
        assert "Aadhaar" not in record.message
        assert "DOB" not in record.message
