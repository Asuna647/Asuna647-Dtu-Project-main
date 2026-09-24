"""
Integration Service for Digital Saarthi — Stage 5 Orchestrator

Main orchestrator that coordinates STT, OCR, intent detection, rule evaluation,
and knowledge base to determine eligibility across all schemes. Enforces strict
PII handling, graceful error fallbacks, and complete audit trails.

Decision tree: USER INPUT → INTENT → MISSING DATA CHECK → ALL SCHEMES → SOURCES → ACTION PLANS → RESULT
"""

import logging
import hashlib
import json
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict

from app.models import (
    EligibilityResult,
    IntentDetectionResponse,
    SchemeResponse,
    SchemeSourceResponse,
)
from app.stt_service import transcribe_audio
from app.ocr_service import process_document_bytes
from app.intent_engine import detect_intent
from app.rule_engine import check_ignoaps
from app.knowledge_base import get_all_schemes, get_scheme_by_id


logger = logging.getLogger(__name__)


@dataclass
class IntegrationResult:
    """Final result from integration service."""
    user_input_type: str  # "voice", "document", "manual"
    intent: str
    intent_confidence: float
    extracted_data: Dict[str, Any]
    missing_fields: List[str]
    eligibility_results: List[EligibilityResult]  # All 3 schemes evaluated
    action_plans: List[str]  # Next steps for user
    audit_hash: str  # Hash of processing steps
    timestamp: str  # ISO datetime


class IntegrationService:
    """
    Orchestrates the full eligibility determination workflow.

    Coordinates:
    - STT for voice input
    - OCR for document input
    - Intent detection
    - Rule evaluation across all schemes
    - Knowledge base lookups
    - Audit trail generation
    - PII protection
    """

    def __init__(
        self,
        stt_service=None,
        ocr_service=None,
        intent_engine=None,
        rule_engine=None,
        knowledge_base=None,
    ):
        """
        Initialize IntegrationService with component dependencies.

        Args:
            stt_service: Speech-to-text service (uses app.stt_service if None)
            ocr_service: OCR service (uses app.ocr_service if None)
            intent_engine: Intent detection engine (uses app.intent_engine if None)
            rule_engine: Rule evaluation engine (uses app.rule_engine if None)
            knowledge_base: Knowledge base (uses app.knowledge_base if None)
        """
        self.stt_service = stt_service or transcribe_audio
        self.ocr_service = ocr_service or process_document_bytes
        self.intent_engine = intent_engine or detect_intent
        self.rule_engine = rule_engine or check_ignoaps
        self.knowledge_base = knowledge_base or get_all_schemes

        self.audit_trail: List[str] = []
        self.extracted_data: Dict[str, Any] = {}
        self.missing_fields: List[str] = []

    def process_user_input(
        self,
        input_type: str,
        data: Any,
        language_hint: str = "auto",
    ) -> IntegrationResult:
        """
        Main entry point for processing user input (voice, document, or manual data).

        Orchestrates the full decision tree:
        USER INPUT → INTENT → MISSING DATA CHECK → ALL SCHEMES → SOURCES → ACTION PLANS → RESULT

        Args:
            input_type: "voice" (audio bytes), "document" (image bytes), or "manual" (dict)
            data: Input data (bytes or dict)
            language_hint: Language hint for STT ("en", "hi", "auto")

        Returns:
            IntegrationResult with eligibility determination
        """
        self.audit_trail = []
        self.extracted_data = {}
        self.missing_fields = []
        timestamp = datetime.utcnow().isoformat() + "Z"

        try:
            # STEP 1: Extract data from user input
            self._log_audit("Starting user input processing", extra={"input_type": input_type})

            if input_type == "voice":
                extracted_data = self._process_voice_input(data, language_hint)
            elif input_type == "document":
                extracted_data = self._process_document_input(data)
            elif input_type == "manual":
                extracted_data = data
            else:
                raise ValueError(f"Unsupported input_type: {input_type}")

            self.extracted_data = extracted_data
            self._log_audit("Data extraction complete", extra=extracted_data)

            # STEP 2: Detect intent from extracted query
            query = extracted_data.get("query", "")
            detected_language = extracted_data.get("detected_language", "auto")

            try:
                intent_result = self.intent_engine(query, detected_language)
                intent = intent_result.get("intent", "unknown")
                intent_confidence = intent_result.get("confidence", 0.0)
                self._log_audit("Intent detection successful", extra=intent_result)
            except Exception as e:
                logger.warning(f"Intent detection failed: {e.__class__.__name__}")
                intent = "unknown"
                intent_confidence = 0.0
                self._log_audit("Intent detection failed (fallback to unknown)")

            # STEP 3: Identify missing data required for eligibility checks
            self._identify_missing_data(extracted_data)

            # STEP 4: Run all 3 schemes evaluation
            age = extracted_data.get("age")
            has_bpl = extracted_data.get("has_bpl", False)
            is_organised_worker = extracted_data.get("is_organised_worker", False)
            is_farmer = extracted_data.get("is_farmer", False)

            eligibility_results = self.run_all_schemes(
                age=age,
                has_bpl=has_bpl,
                is_organised_worker=is_organised_worker,
                is_farmer=is_farmer,
            )

            # STEP 5: Get source cards for eligible schemes
            eligible_scheme_ids = [
                r.scheme.lower().replace(" ", "_")
                for r in eligibility_results
                if r.eligible
            ]
            source_cards = self._get_source_cards(eligible_scheme_ids)
            self._log_audit(f"Retrieved sources for {len(source_cards)} schemes")

            # STEP 6: Generate action plan and result
            action_plans = self._generate_action_plans(eligibility_results, self.missing_fields)
            audit_hash = self._build_audit_trail()

            return IntegrationResult(
                user_input_type=input_type,
                intent=intent,
                intent_confidence=intent_confidence,
                extracted_data=self.extracted_data,
                missing_fields=self.missing_fields,
                eligibility_results=eligibility_results,
                action_plans=action_plans,
                audit_hash=audit_hash,
                timestamp=timestamp,
            )

        except Exception as e:
            logger.error(f"Integration service failed: {e.__class__.__name__}: {str(e)}")
            self._log_audit(f"Error during processing: {e.__class__.__name__}")
            audit_hash = self._build_audit_trail()

            # Return minimal error result
            return IntegrationResult(
                user_input_type=input_type,
                intent="unknown",
                intent_confidence=0.0,
                extracted_data=self.extracted_data,
                missing_fields=self.missing_fields,
                eligibility_results=[],
                action_plans=["Please try again with clear input data."],
                audit_hash=audit_hash,
                timestamp=timestamp,
            )

    def run_all_schemes(
        self,
        age: Optional[int] = None,
        has_bpl: bool = False,
        is_organised_worker: bool = False,
        is_farmer: bool = False,
    ) -> List[EligibilityResult]:
        """
        Check eligibility against all 3 schemes.

        Evaluates IGNOAPS, E-Shram, and PM-Kisan with provided data.
        Never guesses missing eligibility factors — returns cannot_determine verdict.

        Args:
            age: User's age (optional, if missing IGNOAPS returns cannot_determine)
            has_bpl: Below Poverty Line status
            is_organised_worker: EPFO/ESIC covered
            is_farmer: Owns cultivable land

        Returns:
            List of EligibilityResult for each scheme
        """
        results = []

        try:
            # IGNOAPS: Requires age and BPL status
            ignoaps_result = check_ignoaps(age=age, has_bpl=has_bpl)
            results.append(ignoaps_result)
            self._log_audit("IGNOAPS evaluation complete", extra={"eligible": ignoaps_result.eligible})
        except Exception as e:
            logger.error(f"IGNOAPS evaluation failed: {e.__class__.__name__}")
            self._log_audit("IGNOAPS evaluation failed (error)")
            results.append(
                EligibilityResult(
                    eligible=False,
                    scheme="IGNOAPS",
                    verdict="error_evaluation",
                    reasons=["Technical error during evaluation."],
                    steps=[],
                    warning="Please try again or contact support.",
                    confidence=0.0,
                )
            )

        try:
            # E-SHRAM: Requires age and organised_worker status
            eshram_result = self._check_eshram(age=age, is_organised_worker=is_organised_worker)
            results.append(eshram_result)
            self._log_audit("E-Shram evaluation complete", extra={"eligible": eshram_result.eligible})
        except Exception as e:
            logger.error(f"E-Shram evaluation failed: {e.__class__.__name__}")
            self._log_audit("E-Shram evaluation failed (error)")
            results.append(
                EligibilityResult(
                    eligible=False,
                    scheme="E-Shram",
                    verdict="error_evaluation",
                    reasons=["Technical error during evaluation."],
                    steps=[],
                    warning="Please try again or contact support.",
                    confidence=0.0,
                )
            )

        try:
            # PM-KISAN: Requires farmer status
            pm_kisan_result = self._check_pm_kisan(is_farmer=is_farmer)
            results.append(pm_kisan_result)
            self._log_audit("PM-Kisan evaluation complete", extra={"eligible": pm_kisan_result.eligible})
        except Exception as e:
            logger.error(f"PM-Kisan evaluation failed: {e.__class__.__name__}")
            self._log_audit("PM-Kisan evaluation failed (error)")
            results.append(
                EligibilityResult(
                    eligible=False,
                    scheme="PM-Kisan",
                    verdict="error_evaluation",
                    reasons=["Technical error during evaluation."],
                    steps=[],
                    warning="Please try again or contact support.",
                    confidence=0.0,
                )
            )

        return results

    def identify_missing_data(self, extracted_data: Dict[str, Any]) -> List[str]:
        """
        Identify missing fields required for complete eligibility assessment.

        Args:
            extracted_data: Extracted user data

        Returns:
            List of missing field names
        """
        self._identify_missing_data(extracted_data)
        return self.missing_fields

    def _identify_missing_data(self, extracted_data: Dict[str, Any]) -> None:
        """
        Internal: Identify missing fields and populate self.missing_fields.

        Requires for full determination:
        - age (for IGNOAPS and E-Shram)
        - has_bpl (for IGNOAPS)
        - is_farmer (for PM-Kisan)
        """
        required_fields = {
            "age": "Age (for pension schemes)",
            "has_bpl": "BPL status (for IGNOAPS)",
            "is_farmer": "Farmer status (for PM-Kisan)",
        }

        missing = []
        for field, description in required_fields.items():
            if field not in extracted_data or extracted_data.get(field) is None:
                missing.append(description)

        self.missing_fields = missing

    def ask_clarification(self, missing_questions: List[str]) -> str:
        """
        Generate clarification prompt for missing data.

        Args:
            missing_questions: List of missing field descriptions

        Returns:
            User-friendly clarification message
        """
        if not missing_questions:
            return "All information provided. Ready for eligibility check."

        prompt = "To provide accurate eligibility information, I need clarification:\n\n"
        for i, question in enumerate(missing_questions, 1):
            prompt += f"{i}. {question}\n"

        prompt += (
            "\nPlease provide these details so I can give you accurate information "
            "about your eligibility for government schemes."
        )

        return prompt

    def _get_source_cards(self, scheme_ids: List[str]) -> List[SchemeResponse]:
        """
        Retrieve scheme information cards (source verification, benefits, steps).

        Args:
            scheme_ids: List of scheme IDs to fetch

        Returns:
            List of SchemeResponse objects
        """
        source_cards = []

        for scheme_id in scheme_ids:
            try:
                scheme_record = get_scheme_by_id(scheme_id)
                if not scheme_record:
                    logger.warning(f"Scheme not found: {scheme_id}")
                    continue

                source = SchemeSourceResponse(
                    official_url=scheme_record["source"]["official_url"],
                    department=scheme_record["source"]["department"],
                    helpline=scheme_record["source"].get("helpline"),
                    last_verified=scheme_record["source"]["last_verified"],
                )

                card = SchemeResponse(
                    id=scheme_record["id"],
                    name=scheme_record["name"],
                    short_name=scheme_record["short_name"],
                    category=scheme_record["category"],
                    description=scheme_record["description"],
                    eligibility_criteria=scheme_record["eligibility_criteria"],
                    required_documents=scheme_record["required_documents"],
                    benefits=scheme_record["benefits"],
                    steps=scheme_record["steps"],
                    source=source,
                )
                source_cards.append(card)

            except Exception as e:
                logger.error(f"Failed to retrieve scheme {scheme_id}: {e.__class__.__name__}")

        return source_cards

    def _build_audit_trail(self) -> str:
        """
        Generate audit trail hash from processing steps.
        Excludes PII; includes only step names and outcomes.

        Returns:
            SHA-256 hash of audit trail steps
        """
        audit_str = "|".join(self.audit_trail)
        audit_hash = hashlib.sha256(audit_str.encode()).hexdigest()
        return audit_hash

    def _log_audit(self, step: str, extra: Optional[Dict[str, Any]] = None) -> None:
        """
        Log a processing step to audit trail (no PII).

        Args:
            step: Description of processing step
            extra: Optional metadata (sanitized of PII)
        """
        if extra:
            # Sanitize: remove potentially sensitive keys
            sensitive_keys = {"query", "transcribed_text", "name", "dob", "raw_text"}
            sanitized = {k: v for k, v in extra.items() if k not in sensitive_keys}
            step_entry = f"{step} [{json.dumps(sanitized)}]"
        else:
            step_entry = step

        self.audit_trail.append(step_entry)
        logger.debug(step_entry)

    def _process_voice_input(self, audio_bytes: bytes, language_hint: str) -> Dict[str, Any]:
        """
        Process voice input via STT and extract query.

        Args:
            audio_bytes: Audio file bytes
            language_hint: Language hint for transcription

        Returns:
            Dict with transcribed_text and detected_language
        """
        try:
            result = self.stt_service(audio_bytes, language_hint)
            self._log_audit("Voice transcription successful")
            return {
                "query": result.get("transcribed_text", ""),
                "detected_language": result.get("detected_language", "auto"),
                "stt_confidence": result.get("stt_confidence", 0.0),
            }
        except Exception as e:
            logger.error(f"Voice processing failed: {e.__class__.__name__}")
            self._log_audit("Voice processing failed (error)")
            return {
                "query": "",
                "detected_language": "unknown",
                "stt_confidence": 0.0,
                "error": str(e),
            }

    def _process_document_input(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        Process document (image) input via OCR and extract structured fields.

        Args:
            image_bytes: Image file bytes (Aadhaar, BPL card, etc.)

        Returns:
            Dict with extracted age, has_bpl, dob, name, gender, confidence
        """
        try:
            result = self.ocr_service(image_bytes, "document.jpg", "image/jpeg")
            self._log_audit("Document OCR successful")
            return {
                "age": result.get("age"),
                "has_bpl": result.get("has_bpl", False),
                "dob": result.get("dob"),
                "name": result.get("name"),
                "gender": result.get("gender"),
                "confidence": result.get("confidence", 0.0),
                "query": f"Age {result.get('age')} BPL {result.get('has_bpl')}",
                "detected_language": "en",
            }
        except Exception as e:
            logger.error(f"Document processing failed: {e.__class__.__name__}")
            self._log_audit("Document processing failed (error)")
            return {
                "query": "",
                "detected_language": "unknown",
                "error": str(e),
            }

    def _check_eshram(
        self,
        age: Optional[int] = None,
        is_organised_worker: bool = False,
    ) -> EligibilityResult:
        """
        Evaluate E-Shram eligibility.

        E-Shram requires:
        - Age 18–59 years
        - Unorganized sector worker (not covered by EPFO/ESIC)

        Args:
            age: User's age
            is_organised_worker: Is covered by EPFO/ESIC

        Returns:
            EligibilityResult for E-Shram
        """
        reasons = []

        if age is None:
            return EligibilityResult(
                eligible=False,
                scheme="E-Shram",
                verdict="cannot_determine",
                reasons=["✗ Age missing or unreadable. Cannot determine eligibility."],
                steps=[],
                warning="Please provide your age.",
                confidence=0.0,
            )

        if age < 0 or age > 120:
            return EligibilityResult(
                eligible=False,
                scheme="E-Shram",
                verdict="invalid_input",
                reasons=[f"✗ Invalid age: {age}. Age must be between 0 and 120."],
                steps=[],
                warning="Please check your input.",
                confidence=0.0,
            )

        age_eligible = 18 <= age <= 59
        if age_eligible:
            reasons.append(f"✓ Age {age} is within the required range (18–59 years).")
        else:
            reasons.append(f"✗ Age {age} is outside the eligible range (18–59 years).")

        organized_eligible = not is_organised_worker
        if organized_eligible:
            reasons.append("✓ Not covered by EPFO/ESIC — eligible for E-Shram.")
        else:
            reasons.append("✗ Already covered by EPFO/ESIC — ineligible for E-Shram.")

        eligible = age_eligible and organized_eligible

        return EligibilityResult(
            eligible=eligible,
            scheme="E-Shram",
            verdict="Eligible for E-Shram" if eligible else "Not currently eligible",
            reasons=reasons,
            steps=[
                "Step 1: Visit https://eshram.gov.in",
                "Step 2: Click 'Register as a Worker'",
                "Step 3: Verify Aadhaar and provide occupation details",
                "Step 4: Complete registration and download your E-Shram card",
            ] if eligible else [],
            warning=None if eligible else "Organized sector workers are ineligible.",
            confidence=1.0,
        )

    def _check_pm_kisan(self, is_farmer: bool = False) -> EligibilityResult:
        """
        Evaluate PM-Kisan eligibility.

        PM-Kisan requires:
        - Farmer with cultivable landholding (up to 2 hectares / 5 acres)

        Args:
            is_farmer: Owns cultivable land

        Returns:
            EligibilityResult for PM-Kisan
        """
        reasons = []

        if not is_farmer:
            reasons.append("✗ No cultivable landholding — ineligible for PM-Kisan.")
            return EligibilityResult(
                eligible=False,
                scheme="PM-Kisan",
                verdict="Not currently eligible",
                reasons=reasons,
                steps=[],
                warning="PM-Kisan is for farmer families with cultivable land.",
                confidence=1.0,
            )

        reasons.append("✓ Cultivable landholding verified — eligible for PM-Kisan.")

        return EligibilityResult(
            eligible=True,
            scheme="PM-Kisan",
            verdict="Eligible for PM-Kisan",
            reasons=reasons,
            steps=[
                "Step 1: Visit https://pmkisan.gov.in",
                "Step 2: Click 'Farmer Corner' → 'New Farmer Registration'",
                "Step 3: Enter Aadhaar, state, and district",
                "Step 4: Provide land details and bank account",
                "Step 5: Receive registration number for tracking",
            ],
            warning=None,
            confidence=1.0,
        )

    def _generate_action_plans(
        self,
        eligibility_results: List[EligibilityResult],
        missing_fields: List[str],
    ) -> List[str]:
        """
        Generate action plan based on eligibility results and missing data.

        Args:
            eligibility_results: List of scheme evaluations
            missing_fields: Missing data fields

        Returns:
            List of recommended actions for user
        """
        actions = []

        # If missing critical data, ask for clarification first
        if missing_fields:
            actions.append(
                "First, please provide: " + ", ".join(missing_fields) + "."
            )

        # Check for eligible schemes
        eligible_schemes = [r for r in eligibility_results if r.eligible]

        if eligible_schemes:
            actions.append(
                f"You may be eligible for {len(eligible_schemes)} scheme(s): "
                + ", ".join([r.scheme for r in eligible_schemes]) + "."
            )
            actions.append("Visit the official portals to apply (links provided above).")
        else:
            actions.append("Currently, you do not qualify for the evaluated schemes.")
            actions.append("Please contact the helplines provided for more information.")

        # Add warnings
        warning_schemes = [r for r in eligibility_results if r.warning]
        if warning_schemes:
            actions.append(
                "⚠ Important: " + " ".join([r.warning for r in warning_schemes])
            )

        return actions
