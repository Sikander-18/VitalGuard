"""
VitalGuard v2 — Emergency Service
Handles SMS, Voice Calls, and Doctor Email notifications.
Implements:
  - ONE-SHOT incident locking to prevent alert spam
  - Retry logic (3 attempts with exponential backoff)
  - Escalation chain
  - Structured logging
"""

import logging
import smtplib
import ssl
import time
from email.message import EmailMessage
from typing import Optional

from ..config import settings

logger = logging.getLogger("vitalguard.emergency")

MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 1.0  # seconds


def _safe_print(text: str):
    """Print text safely on Windows consoles that can't handle Unicode emoji."""
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode("ascii", errors="replace").decode("ascii"))


# ────────────────────────────────────────────────────────────────
# ONE-SHOT INCIDENT LOCK
# ────────────────────────────────────────────────────────────────

_fired: dict = {
    "sms_patient": False,
    "sms_emergency": False,
    "voice_emergency": False,
    "email_doctor": False,
}

_normal_streak = 0
RESET_AFTER_N_NORMAL = 3


def reset_incident():
    """Reset all one-shot locks — call when patient is back to normal."""
    global _normal_streak
    for key in _fired:
        _fired[key] = False
    _normal_streak = 0
    logger.info("Incident reset — all action locks cleared.")


def update_incident_state(condition: str):
    """Track consecutive normal readings. Reset after N consecutive normals."""
    global _normal_streak
    if condition == "normal":
        _normal_streak += 1
        if _normal_streak >= RESET_AFTER_N_NORMAL:
            reset_incident()
    else:
        _normal_streak = 0


def try_fire(action_type: str) -> bool:
    """Returns True (and marks as fired) if action hasn't fired yet this incident."""
    if _fired.get(action_type, False):
        return False
    _fired[action_type] = True
    return True


def unfire(action_type: str):
    """Reset a single lock — used when ALL send attempts failed."""
    _fired[action_type] = False


def get_incident_status() -> dict:
    """Get the current state of all incident locks."""
    return {k: ("fired" if v else "ready") for k, v in _fired.items()}


# ────────────────────────────────────────────────────────────────
# EMERGENCY SERVICE
# ────────────────────────────────────────────────────────────────

class EmergencyService:
    def __init__(self):
        self.client = None
        self.from_number = settings.TWILIO_PHONE_NUMBER

        if settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN:
            try:
                from twilio.rest import Client
                self.client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
                logger.info(f"Twilio Client initialized: {self.from_number}")
            except Exception as e:
                logger.warning(f"Twilio init failed: {e}")
        else:
            logger.warning("Twilio credentials not configured — using mock mode")

    # ── SMS with Retry ───────────────────────────────────────────

    def trigger_sms(self, phone: str, message: str) -> dict:
        """Send SMS with retry logic (3 attempts, exponential backoff)."""
        if not self.client or not settings.TWILIO_ENABLED:
            _safe_print(f"\n--- MOCK SMS ---\nTo: {phone}\n{message}\n----------------\n")
            return {"mode": "mock", "status": "mock_sent"}

        last_error = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                msg = self.client.messages.create(
                    body=message,
                    from_=self.from_number,
                    to=phone,
                )
                logger.info(f"SMS sent to {phone} (attempt {attempt}) | SID: {msg.sid}")
                return {"mode": "live", "sid": msg.sid, "status": msg.status, "attempt": attempt}
            except Exception as e:
                last_error = str(e)
                logger.warning(f"SMS attempt {attempt}/{MAX_RETRIES} failed: {e}")
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_BACKOFF_BASE * (2 ** (attempt - 1)))

        _safe_print(f"\n--- MOCK SMS FALLBACK (after {MAX_RETRIES} retries) ---\n"
                    f"To: {phone}\n{message}\n---\n")
        return {"mode": "mock", "status": "mock_fallback", "error": last_error, "attempts": MAX_RETRIES}

    # ── Voice Call with Retry ────────────────────────────────────

    def trigger_call(self, phone: str, message: str) -> dict:
        """Place voice call with retry logic."""
        if not self.client or not settings.TWILIO_ENABLED:
            _safe_print(f"\n--- MOCK VOICE CALL ---\nTo: {phone}\n{message}\n-----------------------\n")
            return {"mode": "mock", "status": "mock_call"}

        last_error = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                twiml = f'<Response><Say voice="alice">{message}</Say></Response>'
                call = self.client.calls.create(
                    to=phone,
                    from_=self.from_number,
                    twiml=twiml,
                )
                logger.info(f"Voice call to {phone} (attempt {attempt}) | SID: {call.sid}")
                return {"mode": "live", "call_sid": call.sid, "status": call.status, "attempt": attempt}
            except Exception as e:
                last_error = str(e)
                logger.warning(f"Voice call attempt {attempt}/{MAX_RETRIES} failed: {e}")
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_BACKOFF_BASE * (2 ** (attempt - 1)))

        _safe_print(f"\n--- MOCK VOICE CALL FALLBACK ---\nTo: {phone}\n{message}\n--------------------------------\n")
        return {"mode": "mock", "status": "call_failed", "error": last_error, "attempts": MAX_RETRIES}

    # ── Email ────────────────────────────────────────────────────

    def send_doctor_email(self, subject: str, body: str) -> dict:
        """Send email to doctor via SMTP SSL."""
        if not settings.EMAIL_ENABLED or not settings.SMTP_USERNAME or not settings.SMTP_PASSWORD:
            _safe_print(f"\n--- MOCK EMAIL ---\nTo: {settings.DOCTOR_EMAIL}\n"
                        f"Subject: {subject}\n{body}\n------------------\n")
            return {"mode": "mock", "status": "mock_email"}

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                msg = EmailMessage()
                msg.set_content(body)
                msg["Subject"] = subject
                msg["From"] = settings.SMTP_USERNAME
                msg["To"] = settings.DOCTOR_EMAIL

                context = ssl.create_default_context()
                with smtplib.SMTP_SSL(settings.SMTP_SERVER, settings.SMTP_PORT, context=context) as server:
                    server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
                    server.send_message(msg)

                logger.info(f"Email sent to {settings.DOCTOR_EMAIL} (attempt {attempt})")
                return {"mode": "live", "status": "email_sent", "attempt": attempt}
            except Exception as e:
                logger.warning(f"Email attempt {attempt}/{MAX_RETRIES} failed: {e}")
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_BACKOFF_BASE)

        _safe_print(f"\n--- MOCK EMAIL FALLBACK ---\nTo: {settings.DOCTOR_EMAIL}\n"
                    f"Subject: {subject}\n{body}\n---------------------------\n")
        return {"mode": "mock", "status": "email_fallback"}


# Global instance
emergency_service = EmergencyService()
