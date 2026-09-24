"""
Action Plan Generator — Stage 5

Generates actionable next-steps based on eligibility outcome.
Provides scheme-specific application steps, document requirements, timing estimates,
and contact information in multiple languages (English and Hindi).

Safety Rules:
- Never promise unverified benefits
- Always cite official sources
- Include helpline numbers
- Mention that verification is needed
"""

from typing import List, Dict, Optional
from enum import Enum


class Language(str, Enum):
    """Supported languages for action plans."""
    ENGLISH = "en"
    HINDI = "hi"


class ActionPlanGenerator:
    """
    Generates actionable next-steps for users based on eligibility outcomes.

    Main entrypoint: generate_plan()
    Returns structured action plans with steps, documents, timing, and contact info.
    """

    # Scheme-specific application steps (English)
    IGNOAPS_ELIGIBLE_STEPS_EN = [
        {
            "step": 1,
            "title": "Visit Your Local Gram Panchayat or Ward Office",
            "description": "Visit the Social Welfare Department or your nearest Gram Panchayat office during office hours (9 AM - 5 PM).",
            "duration": "1-2 hours",
            "documents": ["Aadhaar Card", "BPL Ration Card", "Bank Passbook"],
        },
        {
            "step": 2,
            "title": "Obtain and Complete Form P-1",
            "description": "Request Form P-1 for IGNOAPS Old Age Pension. The officer will guide you through filling it. You can also download it from the official website.",
            "duration": "30 minutes",
            "documents": ["Completed Form P-1"],
        },
        {
            "step": 3,
            "title": "Prepare Required Documents",
            "description": "Prepare self-attested copies (your signature on photocopy) of Aadhaar, BPL Ration Card, and Bank Passbook (first page).",
            "duration": "30 minutes",
            "documents": ["2 copies each of Aadhaar, BPL Card, Bank Passbook"],
        },
        {
            "step": 4,
            "title": "Submit Application",
            "description": "Submit your completed form and documents to the Social Welfare Officer. Collect the receipt with date and reference number.",
            "duration": "30 minutes",
            "documents": ["Receipt with application number"],
        },
        {
            "step": 5,
            "title": "Verification Process",
            "description": "Officials will verify your documents within 15-20 days. You may receive a home visit. Keep your phone reachable.",
            "duration": "15-20 days",
            "documents": [],
        },
        {
            "step": 6,
            "title": "Approval and Bank Transfer",
            "description": "Once approved, pension will be credited directly to your bank account every month. Usually begins within 1-2 months.",
            "duration": "1-2 months",
            "documents": [],
        },
    ]

    IGNOAPS_ELIGIBLE_STEPS_HI = [
        {
            "step": 1,
            "title": "अपने स्थानीय ग्राम पंचायत या वार्ड कार्यालय में जाएं",
            "description": "सामाजिक कल्याण विभाग या अपने निकटतम ग्राम पंचायत कार्यालय में कार्यालय के समय (सुबह 9 बजे - शाम 5 बजे) जाएं।",
            "duration": "1-2 घंटे",
            "documents": ["आधार कार्ड", "बीपीएल राशन कार्ड", "बैंक पासबुक"],
        },
        {
            "step": 2,
            "title": "फॉर्म पी-1 प्राप्त करें और भरें",
            "description": "IGNOAPS वृद्धा पेंशन के लिए फॉर्म पी-1 मांगें। अधिकारी आपको भरने में मार्गदर्शन देंगे। आप इसे आधिकारिक वेबसाइट से भी डाउनलोड कर सकते हैं।",
            "duration": "30 मिनट",
            "documents": ["भरा हुआ फॉर्म पी-1"],
        },
        {
            "step": 3,
            "title": "आवश्यक दस्तावेज़ तैयार करें",
            "description": "आधार, बीपीएल कार्ड और बैंक पासबुक (प्रथम पृष्ठ) की स्व-सत्यापित प्रतियां (आपके हस्ताक्षर के साथ) तैयार करें।",
            "duration": "30 मिनट",
            "documents": ["आधार, बीपीएल कार्ड, बैंक पासबुक की 2-2 प्रतियां"],
        },
        {
            "step": 4,
            "title": "आवेदन जमा करें",
            "description": "सामाजिक कल्याण अधिकारी को अपना भरा हुआ फॉर्म और दस्तावेज़ जमा करें। तारीख और संदर्भ संख्या वाली रसीद लें।",
            "duration": "30 मिनट",
            "documents": ["आवेदन संख्या के साथ रसीद"],
        },
        {
            "step": 5,
            "title": "सत्यापन प्रक्रिया",
            "description": "अधिकारी 15-20 दिनों में आपके दस्तावेज़ों का सत्यापन करेंगे। आपको घर पर मिल सकते हैं। अपना फोन हमेशा उपलब्ध रखें।",
            "duration": "15-20 दिन",
            "documents": [],
        },
        {
            "step": 6,
            "title": "मंजूरी और बैंक ट्रांसफर",
            "description": "मंजूरी के बाद, पेंशन हर महीने सीधे आपके बैंक खाते में जमा होगी। आमतौर पर 1-2 महीने में शुरू होती है।",
            "duration": "1-2 महीने",
            "documents": [],
        },
    ]

    IGNOAPS_INELIGIBLE_STEPS_EN = [
        {
            "step": 1,
            "title": "Apply for Below Poverty Line (BPL) Ration Card",
            "description": "Visit your nearest Tehsil/Block office or Common Service Centre (CSC). Bring income proof (pay slip, land records, or income certificate from Gram Panchayat).",
            "duration": "1-2 hours",
            "documents": ["Income proof", "Identity proof (Aadhaar)", "Address proof"],
        },
        {
            "step": 2,
            "title": "Submit BPL Application",
            "description": "Complete the BPL application form at the Tehsil office. Keep your receipt for tracking.",
            "duration": "1 hour",
            "documents": ["Application receipt"],
        },
        {
            "step": 3,
            "title": "Wait for BPL Card Approval",
            "description": "The verification process takes 15-30 days. You will be notified via SMS or phone once approved.",
            "duration": "15-30 days",
            "documents": [],
        },
        {
            "step": 4,
            "title": "Collect Your BPL Card",
            "description": "Once approved, collect your BPL card from the Tehsil office. You must bring an ID proof.",
            "duration": "1 hour",
            "documents": ["BPL Ration Card"],
        },
        {
            "step": 5,
            "title": "Apply for IGNOAPS Pension",
            "description": "After receiving your BPL card, follow the IGNOAPS eligibility steps (Step 1-6 above) to apply for the pension.",
            "duration": "As per IGNOAPS steps",
            "documents": ["BPL Card", "Aadhaar", "Bank Passbook"],
        },
    ]

    IGNOAPS_INELIGIBLE_STEPS_HI = [
        {
            "step": 1,
            "title": "बीपीएल (गरीबी रेखा से नीचे) राशन कार्ड के लिए आवेदन करें",
            "description": "अपने निकटतम तहसील/ब्लॉक कार्यालय या कॉमन सर्विस सेंटर (सीएससी) जाएं। आय का प्रमाण लाएं (पे स्लिप, भूमि रिकॉर्ड या ग्राम पंचायत से आय प्रमाण पत्र)।",
            "duration": "1-2 घंटे",
            "documents": ["आय का प्रमाण", "पहचान प्रमाण (आधार)", "पता प्रमाण"],
        },
        {
            "step": 2,
            "title": "बीपीएल आवेदन जमा करें",
            "description": "तहसील कार्यालय में बीपीएल आवेदन फॉर्म भरें। ट्रैकिंग के लिए अपनी रसीद रखें।",
            "duration": "1 घंटा",
            "documents": ["आवेदन रसीद"],
        },
        {
            "step": 3,
            "title": "बीपीएल कार्ड की मंजूरी का प्रतीक्षा करें",
            "description": "सत्यापन प्रक्रिया में 15-30 दिन लगते हैं। मंजूरी के बाद आपको एसएमएस या फोन से सूचित किया जाएगा।",
            "duration": "15-30 दिन",
            "documents": [],
        },
        {
            "step": 4,
            "title": "अपना बीपीएल कार्ड लें",
            "description": "मंजूरी के बाद, तहसील कार्यालय से अपना बीपीएल कार्ड लें। आपको पहचान प्रमाण लाना होगा।",
            "duration": "1 घंटा",
            "documents": ["बीपीएल राशन कार्ड"],
        },
        {
            "step": 5,
            "title": "IGNOAPS पेंशन के लिए आवेदन करें",
            "description": "बीपीएल कार्ड प्राप्त करने के बाद, IGNOAPS पेंशन के लिए आवेदन करने के लिए ऊपर दिए गए चरणों (चरण 1-6) का पालन करें।",
            "duration": "IGNOAPS चरणों के अनुसार",
            "documents": ["बीपीएल कार्ड", "आधार", "बैंक पासबुक"],
        },
    ]

    ESHRAM_ELIGIBLE_STEPS_EN = [
        {
            "step": 1,
            "title": "Visit E-Shram Registration Center",
            "description": "Visit your nearest Common Service Centre (CSC) or state labor office. E-Shram registration is free and available online.",
            "duration": "1-2 hours",
            "documents": ["Aadhaar Card", "Mobile Number", "Bank Account Details"],
        },
        {
            "step": 2,
            "title": "Complete E-Shram Registration Form",
            "description": "Fill out the E-Shram worker registration form with your personal, work, and bank details. The CSC operator will assist you.",
            "duration": "30 minutes",
            "documents": ["Completed registration form"],
        },
        {
            "step": 3,
            "title": "Verify Your Details",
            "description": "Verify the information on screen. Your Aadhaar will be used for authentication via OTP.",
            "duration": "10 minutes",
            "documents": [],
        },
        {
            "step": 4,
            "title": "Receive E-Shram Number",
            "description": "Once registered, you will receive your unique E-Shram number via SMS. Note it down for future reference.",
            "duration": "Immediate",
            "documents": ["E-Shram Number (12-digit)"],
        },
        {
            "step": 5,
            "title": "Enroll in PMJDY Scheme",
            "description": "The system will enroll you in Pradhan Mantri Jeevan Jyoti Bima Yojana (₹330 annual insurance). Ensure your bank account is active.",
            "duration": "Automatic",
            "documents": [],
        },
        {
            "step": 6,
            "title": "Track Benefits",
            "description": "Visit eshram.gov.in or call the E-Shram helpline to track your benefits and check eligibility for other government schemes.",
            "duration": "Ongoing",
            "documents": [],
        },
    ]

    ESHRAM_ELIGIBLE_STEPS_HI = [
        {
            "step": 1,
            "title": "ई-श्रम पंजीकरण केंद्र पर जाएं",
            "description": "अपने निकटतम कॉमन सर्विस सेंटर (सीएससी) या राज्य श्रम कार्यालय जाएं। ई-श्रम पंजीकरण बिल्कुल मुफ्त है और ऑनलाइन उपलब्ध है।",
            "duration": "1-2 घंटे",
            "documents": ["आधार कार्ड", "मोबाइल नंबर", "बैंक खाते का विवरण"],
        },
        {
            "step": 2,
            "title": "ई-श्रम पंजीकरण फॉर्म भरें",
            "description": "ई-श्रम कर्मचारी पंजीकरण फॉर्म को अपने व्यक्तिगत, कार्य और बैंक विवरण के साथ भरें। सीएससी ऑपरेटर आपकी मदद करेगा।",
            "duration": "30 मिनट",
            "documents": ["भरा हुआ पंजीकरण फॉर्म"],
        },
        {
            "step": 3,
            "title": "अपने विवरण की पुष्टि करें",
            "description": "स्क्रीन पर जानकारी सत्यापित करें। आपके आधार का उपयोग ओटीपी के माध्यम से प्रमाणीकरण के लिए किया जाएगा।",
            "duration": "10 मिनट",
            "documents": [],
        },
        {
            "step": 4,
            "title": "ई-श्रम नंबर प्राप्त करें",
            "description": "पंजीकरण के बाद, आपको एसएमएस के माध्यम से अपना अद्वितीय ई-श्रम नंबर मिलेगा। भविष्य के संदर्भ के लिए इसे नोट करें।",
            "duration": "तुरंत",
            "documents": ["ई-श्रम नंबर (12-अंकीय)"],
        },
        {
            "step": 5,
            "title": "पीएमजेडीवाई योजना में नामांकन करें",
            "description": "सिस्टम आपको प्रधानमंत्री जीवन ज्योति बीमा योजना (₹330 वार्षिक बीमा) में नामांकित करेगा। सुनिश्चित करें कि आपका बैंक खाता सक्रिय है।",
            "duration": "स्वचालित",
            "documents": [],
        },
        {
            "step": 6,
            "title": "लाभों को ट्रैक करें",
            "description": "अपने लाभों को ट्रैक करने और अन्य सरकारी योजनाओं के लिए पात्रता की जांच करने के लिए eshram.gov.in पर जाएं या ई-श्रम हेल्पलाइन को कॉल करें।",
            "duration": "चलती हुई",
            "documents": [],
        },
    ]

    PM_KISAN_ELIGIBLE_STEPS_EN = [
        {
            "step": 1,
            "title": "Register on PM-Kisan Portal",
            "description": "Visit pmkisan.gov.in and click 'New Farmer Registration'. You can also register at your local Gram Panchayat or agricultural office.",
            "duration": "30-45 minutes",
            "documents": ["Aadhaar Card", "Land ownership proof", "Bank Account Number"],
        },
        {
            "step": 2,
            "title": "Enter Your Land and Bank Details",
            "description": "Provide your agricultural land details (size, location) and active bank account where subsidy will be deposited.",
            "duration": "15 minutes",
            "documents": ["Land records/revenue documents", "Bank passbook"],
        },
        {
            "step": 3,
            "title": "Verify Your Information",
            "description": "Review all entered information for accuracy. Aadhaar verification may take 1-2 days.",
            "duration": "1-2 days",
            "documents": [],
        },
        {
            "step": 4,
            "title": "Wait for Approval",
            "description": "Your application will be processed within 3-5 business days. You will receive an SMS confirmation.",
            "duration": "3-5 days",
            "documents": [],
        },
        {
            "step": 5,
            "title": "First Installment Credited",
            "description": "Once approved, your first installment of ₹2,000 will be credited within 2-4 weeks. Three installments are released every year (April, August, December).",
            "duration": "2-4 weeks",
            "documents": [],
        },
        {
            "step": 6,
            "title": "Track Your Benefits",
            "description": "Log in to pmkisan.gov.in with your mobile number to check payment status and upcoming installments.",
            "duration": "Ongoing",
            "documents": [],
        },
    ]

    PM_KISAN_ELIGIBLE_STEPS_HI = [
        {
            "step": 1,
            "title": "पीएम-किसान पोर्टल पर पंजीकरण करें",
            "description": "pmkisan.gov.in पर जाएं और 'नया किसान पंजीकरण' पर क्लिक करें। आप अपने स्थानीय ग्राम पंचायत या कृषि कार्यालय में भी पंजीकरण कर सकते हैं।",
            "duration": "30-45 मिनट",
            "documents": ["आधार कार्ड", "भूमि स्वामित्व प्रमाण", "बैंक खाता संख्या"],
        },
        {
            "step": 2,
            "title": "अपने भूमि और बैंक विवरण दर्ज करें",
            "description": "अपने कृषि भूमि का विवरण (आकार, स्थान) और वह सक्रिय बैंक खाता प्रदान करें जहां सब्सिडी जमा होगी।",
            "duration": "15 मिनट",
            "documents": ["भूमि रिकॉर्ड/राजस्व दस्तावेज़", "बैंक पासबुक"],
        },
        {
            "step": 3,
            "title": "अपनी जानकारी सत्यापित करें",
            "description": "सभी दर्ज जानकारी की सटीकता के लिए समीक्षा करें। आधार सत्यापन में 1-2 दिन लग सकते हैं।",
            "duration": "1-2 दिन",
            "documents": [],
        },
        {
            "step": 4,
            "title": "मंजूरी का प्रतीक्षा करें",
            "description": "आपके आवेदन को 3-5 कार्य दिवसों में संसाधित किया जाएगा। आपको एसएमएस पुष्टिकरण मिलेगा।",
            "duration": "3-5 दिन",
            "documents": [],
        },
        {
            "step": 5,
            "title": "पहली किस्त जमा होगी",
            "description": "मंजूरी के बाद, आपकी पहली किस्त ₹2,000 2-4 हफ्तों में जमा होगी। तीन किस्तें साल में (अप्रैल, अगस्त, दिसंबर) जारी की जाती हैं।",
            "duration": "2-4 हफ्ते",
            "documents": [],
        },
        {
            "step": 6,
            "title": "अपने लाभों को ट्रैक करें",
            "description": "अपने मोबाइल नंबर के साथ pmkisan.gov.in पर लॉगिन करें ताकि भुगतान स्थिति और आने वाली किस्तें देख सकें।",
            "duration": "चलती हुई",
            "documents": [],
        },
    ]

    # Contact information by scheme
    SCHEME_CONTACTS = {
        "IGNOAPS": {
            "en": {
                "helpline": "+91-1800-110-007 (toll-free)",
                "website": "https://sje.bih.nic.in/",
                "department": "State Social Welfare Department",
                "note": "Please call during office hours (9 AM - 5 PM, Monday-Friday)",
            },
            "hi": {
                "helpline": "+91-1800-110-007 (टोल-फ्री)",
                "website": "https://sje.bih.nic.in/",
                "department": "राज्य सामाजिक कल्याण विभाग",
                "note": "कृपया कार्यालय के समय के दौरान कॉल करें (सुबह 9 बजे - शाम 5 बजे, सोमवार-शुक्रवार)",
            }
        },
        "ESHRAM": {
            "en": {
                "helpline": "1800-110-069 (toll-free)",
                "website": "https://eshram.gov.in/",
                "department": "Ministry of Labour and Employment",
                "note": "Available 24/7. Multilingual support available.",
            },
            "hi": {
                "helpline": "1800-110-069 (टोल-फ्री)",
                "website": "https://eshram.gov.in/",
                "department": "श्रम और रोजगार मंत्रालय",
                "note": "24/7 उपलब्ध। बहुभाषी सहायता उपलब्ध।",
            }
        },
        "PM_KISAN": {
            "en": {
                "helpline": "1800-165-1551 (toll-free)",
                "website": "https://pmkisan.gov.in/",
                "department": "Ministry of Agriculture & Farmers Welfare",
                "note": "Available 9 AM - 6 PM, Monday-Friday. Agricultural helpline also available.",
            },
            "hi": {
                "helpline": "1800-165-1551 (टोल-फ्री)",
                "website": "https://pmkisan.gov.in/",
                "department": "कृषि और किसान कल्याण मंत्रालय",
                "note": "सुबह 9 बजे - शाम 6 बजे, सोमवार-शुक्रवार उपलब्ध। कृषि हेल्पलाइन भी उपलब्ध है।",
            }
        }
    }

    def generate_plan(
        self,
        eligible: bool,
        scheme_id: str,
        verdict: str,
        missing_data: Optional[List[str]] = None,
        user_language: str = "en",
    ) -> Dict:
        """
        Main entry point to generate an action plan based on eligibility outcome.

        Args:
            eligible: Whether user is eligible for the scheme
            scheme_id: Scheme identifier (IGNOAPS, ESHRAM, PM_KISAN)
            verdict: Eligibility verdict (eligible, not_eligible, cannot_determine)
            missing_data: List of missing fields if cannot_determine
            user_language: User's language preference ('en' or 'hi')

        Returns:
            Dictionary containing structured action plan with steps, documents,
            contacts, and multilingual support.
        """
        language = Language.ENGLISH if user_language == "en" else Language.HINDI

        if verdict == "eligible":
            return self.generate_eligible_plan(scheme_id, language)
        elif verdict == "cannot_determine":
            return self.generate_cannot_determine_plan(missing_data or [], language)
        else:
            return self.generate_ineligible_plan(scheme_id, missing_data or [], language)

    def generate_eligible_plan(
        self, scheme_id: str, language: Language = Language.ENGLISH
    ) -> Dict:
        """
        Generate action plan for eligible users.

        Args:
            scheme_id: Target scheme identifier
            language: Language for steps (English or Hindi)

        Returns:
            Complete action plan with application steps and contact information.
        """
        steps = []
        contact = {}

        if scheme_id == "IGNOAPS":
            steps = (
                self.IGNOAPS_ELIGIBLE_STEPS_EN
                if language == Language.ENGLISH
                else self.IGNOAPS_ELIGIBLE_STEPS_HI
            )
            contact = self.SCHEME_CONTACTS["IGNOAPS"][language.value]
        elif scheme_id == "ESHRAM":
            steps = (
                self.ESHRAM_ELIGIBLE_STEPS_EN
                if language == Language.ENGLISH
                else self.ESHRAM_ELIGIBLE_STEPS_HI
            )
            contact = self.SCHEME_CONTACTS["ESHRAM"][language.value]
        elif scheme_id == "PM_KISAN":
            steps = (
                self.PM_KISAN_ELIGIBLE_STEPS_EN
                if language == Language.ENGLISH
                else self.PM_KISAN_ELIGIBLE_STEPS_HI
            )
            contact = self.SCHEME_CONTACTS["PM_KISAN"][language.value]

        return {
            "status": "eligible",
            "scheme_id": scheme_id,
            "action_steps": steps,
            "contact_info": contact,
            "total_steps": len(steps),
            "language": language.value,
            "warning": self._get_eligible_warning(language),
        }

    def generate_ineligible_plan(
        self, scheme_id: str, missing_fields: List[str], language: Language = Language.ENGLISH
    ) -> Dict:
        """
        Generate action plan to help user become eligible.

        Args:
            scheme_id: Target scheme identifier
            missing_fields: Fields that make user ineligible
            language: Language for steps

        Returns:
            Action plan with steps to become eligible.
        """
        steps = []
        contact = {}

        if scheme_id == "IGNOAPS":
            steps = (
                self.IGNOAPS_INELIGIBLE_STEPS_EN
                if language == Language.ENGLISH
                else self.IGNOAPS_INELIGIBLE_STEPS_HI
            )
            contact = self.SCHEME_CONTACTS["IGNOAPS"][language.value]
        elif scheme_id == "ESHRAM":
            steps = (
                self.ESHRAM_ELIGIBLE_STEPS_EN
                if language == Language.ENGLISH
                else self.ESHRAM_ELIGIBLE_STEPS_HI
            )
            contact = self.SCHEME_CONTACTS["ESHRAM"][language.value]
        elif scheme_id == "PM_KISAN":
            steps = (
                self.PM_KISAN_ELIGIBLE_STEPS_EN
                if language == Language.ENGLISH
                else self.PM_KISAN_ELIGIBLE_STEPS_HI
            )
            contact = self.SCHEME_CONTACTS["PM_KISAN"][language.value]

        return {
            "status": "ineligible",
            "scheme_id": scheme_id,
            "reason": f"Missing or invalid: {', '.join(missing_fields)}",
            "action_steps": steps,
            "contact_info": contact,
            "total_steps": len(steps),
            "language": language.value,
            "warning": self._get_ineligible_warning(language),
        }

    def generate_cannot_determine_plan(
        self, missing_fields: List[str], language: Language = Language.ENGLISH
    ) -> Dict:
        """
        Generate action plan when eligibility cannot be determined.

        Args:
            missing_fields: Fields needed to determine eligibility
            language: Language for instructions

        Returns:
            Plan with steps to gather missing data.
        """
        lang = language.value
        steps = (
            self._get_cannot_determine_steps_en(missing_fields)
            if language == Language.ENGLISH
            else self._get_cannot_determine_steps_hi(missing_fields)
        )

        return {
            "status": "cannot_determine",
            "missing_fields": missing_fields,
            "action_steps": steps,
            "contact_info": {
                "note": (
                    "Contact your local Common Service Centre (CSC) for document verification assistance."
                    if lang == "en"
                    else "दस्तावेज़ सत्यापन सहायता के लिए अपने स्थानीय कॉमन सर्विस सेंटर (सीएससी) से संपर्क करें।"
                )
            },
            "language": lang,
            "warning": self._get_cannot_determine_warning(language),
        }

    def generate_alternative_schemes(
        self, primary_ineligible: str, language: Language = Language.ENGLISH
    ) -> Dict:
        """
        Generate alternative scheme recommendations when primary is ineligible.

        Args:
            primary_ineligible: Primary scheme user is ineligible for
            language: Language for recommendations

        Returns:
            List of alternative schemes with brief descriptions.
        """
        alternatives = []

        if primary_ineligible == "IGNOAPS":
            alternatives = ["ESHRAM", "PM_KISAN"] if primary_ineligible != "ESHRAM" else ["PM_KISAN"]
        elif primary_ineligible == "ESHRAM":
            alternatives = ["IGNOAPS", "PM_KISAN"]
        elif primary_ineligible == "PM_KISAN":
            alternatives = ["IGNOAPS", "ESHRAM"]

        lang = language.value
        return {
            "primary_scheme": primary_ineligible,
            "alternative_schemes": alternatives,
            "message": (
                f"You may be eligible for other schemes. Please check: {', '.join(alternatives)}"
                if lang == "en"
                else f"आप अन्य योजनाओं के लिए पात्र हो सकते हैं। कृपया जांचें: {', '.join(alternatives)}"
            ),
            "language": lang,
        }

    @staticmethod
    def _get_cannot_determine_steps_en(missing_fields: List[str]) -> List[Dict]:
        """Generate steps to gather missing data (English)."""
        steps = []
        if "age" in missing_fields:
            steps.append({
                "step": len(steps) + 1,
                "title": "Obtain Your Age/Date of Birth",
                "description": "Get a clear scan or photocopy of your Aadhaar card showing your date of birth.",
                "documents": ["Aadhaar Card (clear copy)"],
            })
        if "bpl_status" in missing_fields:
            steps.append({
                "step": len(steps) + 1,
                "title": "Get Your BPL Status Verified",
                "description": "Visit your Gram Panchayat with your ration card to verify BPL status.",
                "documents": ["Ration Card", "Income proof"],
            })
        if "land_ownership" in missing_fields:
            steps.append({
                "step": len(steps) + 1,
                "title": "Gather Land Ownership Proof",
                "description": "Collect your land records (mutation, revenue certificate, or lease document).",
                "documents": ["Land deed or revenue records"],
            })
        if not steps:
            steps.append({
                "step": 1,
                "title": "Verify Your Documents",
                "description": "Ensure all your identity and financial documents are up-to-date and clearly readable.",
                "documents": ["All relevant identity and financial documents"],
            })
        return steps

    @staticmethod
    def _get_cannot_determine_steps_hi(missing_fields: List[str]) -> List[Dict]:
        """Generate steps to gather missing data (Hindi)."""
        steps = []
        if "age" in missing_fields:
            steps.append({
                "step": len(steps) + 1,
                "title": "अपनी आयु/जन्मतिथि प्राप्त करें",
                "description": "अपनी जन्मतिथि दिखाने वाले आधार कार्ड की स्पष्ट स्कैन या फोटोकॉपी प्राप्त करें।",
                "documents": ["आधार कार्ड (स्पष्ट प्रति)"],
            })
        if "bpl_status" in missing_fields:
            steps.append({
                "step": len(steps) + 1,
                "title": "अपनी बीपीएल स्थिति सत्यापित करवाएं",
                "description": "बीपीएल स्थिति सत्यापित करने के लिए अपने राशन कार्ड के साथ ग्राम पंचायत जाएं।",
                "documents": ["राशन कार्ड", "आय का प्रमाण"],
            })
        if "land_ownership" in missing_fields:
            steps.append({
                "step": len(steps) + 1,
                "title": "भूमि स्वामित्व प्रमाण एकत्र करें",
                "description": "अपने भूमि रिकॉर्ड (प्रस्तुति, राजस्व प्रमाणपत्र या पट्टा दस्तावेज़) एकत्र करें।",
                "documents": ["भूमि पत्र या राजस्व रिकॉर्ड"],
            })
        if not steps:
            steps.append({
                "step": 1,
                "title": "अपने दस्तावेज़ों की जांच करें",
                "description": "सुनिश्चित करें कि आपके सभी पहचान और वित्तीय दस्तावेज़ अद्यतन हैं और स्पष्ट रूप से पठनीय हैं।",
                "documents": ["सभी प्रासंगिक पहचान और वित्तीय दस्तावेज़"],
            })
        return steps

    @staticmethod
    def _get_eligible_warning(language: Language) -> str:
        """Warning for eligible users (English/Hindi)."""
        if language == Language.ENGLISH:
            return (
                "IMPORTANT: This is not an official approval. You must complete all steps above "
                "and submit your application to the government office. No fees are charged for any "
                "government scheme application. If anyone asks for money, report them to local authorities."
            )
        else:
            return (
                "महत्वपूर्ण: यह आधिकारिक स्वीकृति नहीं है। आपको ऊपर दिए गए सभी चरणों को पूरा करना चाहिए "
                "और सरकारी कार्यालय में अपना आवेदन जमा करना चाहिए। किसी भी सरकारी योजना आवेदन के लिए कोई शुल्क नहीं है। "
                "यदि कोई आपसे पैसे मांगे, तो स्थानीय प्राधिकारियों को रिपोर्ट करें।"
            )

    @staticmethod
    def _get_ineligible_warning(language: Language) -> str:
        """Warning for ineligible users (English/Hindi)."""
        if language == Language.ENGLISH:
            return (
                "Do not pay any fees to become eligible. Government processes are completely free. "
                "Follow official channels only. If you encounter any scams, report immediately to local authorities."
            )
        else:
            return (
                "पात्र बनने के लिए कोई शुल्क न दें। सरकारी प्रक्रियाएं पूरी तरह मुफ्त हैं। "
                "केवल आधिकारिक चैनलों का पालन करें। यदि आप किसी घोटाले का सामना करते हैं, तो तुरंत स्थानीय अधिकारियों को रिपोर्ट करें।"
            )

    @staticmethod
    def _get_cannot_determine_warning(language: Language) -> str:
        """Warning when eligibility cannot be determined (English/Hindi)."""
        if language == Language.ENGLISH:
            return (
                "Please gather the missing documents listed above. Once you have them, you can resubmit "
                "your information for a complete eligibility check. All assistance is free."
            )
        else:
            return (
                "कृपया ऊपर सूचीबद्ध लापता दस्तावेज़ एकत्र करें। एक बार आपके पास उपलब्ध होने के बाद, आप पूर्ण पात्रता जांच के लिए अपनी जानकारी फिर से जमा कर सकते हैं। "
                "सभी सहायता मुफ्त है।"
            )
