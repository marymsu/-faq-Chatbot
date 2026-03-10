"""
nlp.py — Gemini-powered NLP fallback for Campus Buddy chatbot.

Called only when the keyword-based DB lookup returns no match.
Scoped strictly to campus / business context via system instruction.
"""

import os
import google.generativeai as genai

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

SYSTEM_INSTRUCTION = """
You are Campus Buddy, a helpful assistant for a campus furniture and supplies business.
You only answer questions related to:
- Campus furniture products (tables, chairs, stands, etc.)
- Pricing, discounts, and promotions
- Delivery, shipping, and logistics
- Customization options
- Payment methods
- Warranty and return policies
- General campus business inquiries

If a question is completely unrelated to campus life, furniture, or this business,
politely respond: "I'm only able to help with campus and business-related questions.
Please contact us directly for other inquiries."

Keep responses concise, friendly, and professional.
Do NOT make up specific prices or policies — if you're unsure, say so and suggest
the user contact the business directly.
"""

# ---------------------------------------------------------------------------
# Gemini client (lazy-initialised so missing key doesn't crash on import)
# ---------------------------------------------------------------------------

_model = None


def _get_model():
    global _model
    if _model is None:
        if not GEMINI_API_KEY:
            raise EnvironmentError(
                "GEMINI_API_KEY environment variable is not set. "
                "Please set it before starting the application."
            )
        genai.configure(api_key=GEMINI_API_KEY)
        _model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            system_instruction=SYSTEM_INSTRUCTION,
        )
    return _model


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_nlp_response(user_message: str) -> str:
    """
    Send *user_message* to Gemini and return the response text.

    Returns a safe fallback string if the API key is missing or the
    request fails, so the chatbot never crashes.
    """
    if not user_message or not user_message.strip():
        return "Please say something."

    try:
        model = _get_model()
        response = model.generate_content(user_message)
        return response.text.strip()

    except EnvironmentError as exc:
        # API key not configured — tell the admin, give user a soft message
        print(f"[NLP] Configuration error: {exc}")
        return (
            "I'm not sure about that yet. Please contact us directly "
            "or check back later — our team is always updating my knowledge!"
        )

    except Exception as exc:
        # Network errors, quota exceeded, safety filters, etc.
        print(f"[NLP] Gemini API error: {exc}")
        return (
            "I'm having trouble understanding that right now. "
            "Please try rephrasing, or contact us directly for assistance."
        )
