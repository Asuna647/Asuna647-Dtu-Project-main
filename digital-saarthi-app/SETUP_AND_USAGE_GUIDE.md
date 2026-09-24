# Setup and Usage Guide for Digital Saarthi

This guide helps you set up and use the Digital Saarthi application.

## 1. Quick Start (5 min)
### Prerequisites
- Python 3.10+
- pip

### Setup
1. Open a terminal in the project root directory.
2. Navigate to the backend directory: `cd backend`
3. Install dependencies: `pip install -r requirements.txt` (or simply `pip install fastapi uvicorn pydantic python-multipart` if requirements.txt is missing)
4. Start the backend: `python -m app.main`

## 2. Running Frontend
- Open `frontend/index.html` directly in your browser.
- Or, for better compatibility, run a local server:
  - `cd frontend`
  - `python -m http.server 8080`
  - Open `http://localhost:8080` in your browser.

## 3. Step-by-Step Usage
a) **Manual form**: Select "Manual Form", fill Age, BPL, Occupation, and click "Check Eligibility".
b) **Voice**: Click "Voice Input", click "Start Recording", speak your details, and wait for processing.
c) **Document**: Select "Document", upload your card, click "Process Document", confirm values, then check eligibility.

## 4. Understanding Results
- **Green** = Eligible
- **Amber** = Cannot determine
- **Gray** = Ineligible
- Each shows: reason, benefits, next steps, and helpline.

## 5. API Docs
- Access interactive API documentation at: `http://localhost:8000/docs`

## 6. Running Tests
- Run the full test suite: `pytest backend/tests/ -v`

## 7. Troubleshooting
- **Microphone**: Ensure browser permissions for microphone are granted.
- **Document Issues**: Use clear images (JPEG/PNG).
- **API Connection**: Ensure the backend is running on port 8000.

## 8. Architecture
- Decisions are made by deterministic rules.
- LLM provides explanations for verified decisions.
- User confirmation is mandatory for OCR and voice inputs.

## 9. Hackathon Demo Script (45 sec)
1. **Show**: Open the app and select Manual Form.
2. **Say**: "I am showing how Digital Saarthi makes government schemes accessible."
3. **Action**: Enter details for an elderly BPL citizen (e.g., Age 72, BPL Yes).
4. **Outcome**: The system shows clear eligibility status, benefits, and helpline numbers.
5. **Say**: "We provide deterministic eligibility checks with LLM-powered explanations."
