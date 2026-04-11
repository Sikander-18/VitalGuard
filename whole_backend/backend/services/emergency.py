"""
VitalGuard — Emergency Service
Handles SMS, Voice Calls, and Doctor Email notifications.
Implements ONE-SHOT incident locking to prevent alert spam.
"""

import logging
import smtplib
import ssl
from email.message import EmailMessage
from twilio.rest import Client
from ..config import settings

logger = logging.getLogger(__name__)


# ────────────────────────────────────────────────────────────────
# ONE-SHOT INCIDENT LOCK
#
# Each flag is True = "already fired this incident, skip".
# All flags reset together when patient returns to normal for
# RESET_AFTER_N_NORMAL consecutive readings.
# ────────────────────────────────────────────────────────────────

_fired: dict[str, bool] = {
    "sms_patient":     False,
    "sms_emergency":   False,
    "voice_emergency": False,
    "email_doctor":    False,
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
    """
    Track consecutive normal readings.
    After RESET_AFTER_N_NORMAL consecutive normals, reset the incident
    so the next anomaly will fire fresh alerts again.
    """
    global _normal_streak
    if condition == "normal":
        _normal_streak += 1
        if _normal_streak >= RESET_AFTER_N_NORMAL:
            reset_incident()
    else:
        _normal_streak = 0


def try_fire(action_type: str) -> bool:
    """
    Returns True (and marks as fired) if this action hasn't fired yet.
    Returns False if already fired — caller should skip.
    """
    if _fired.get(action_type, False):
        return False
    _fired[action_type] = True
    return True


def unfire(action_type: str):
    """Reset a single lock — used when ALL send attempts for an action failed."""
    _fired[action_type] = False


def get_incident_status() -> dict:
    """Get the current state of all incident locks."""
    return {k: ("fired" if v else "ready") for k, v in _fired.items()}


# ────────────────────────────────────────────────────────────────
# TWILIO CLIENT
# ────────────────────────────────────────────────────────────────

class EmergencyService:
    def __init__(self):
        if settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN:
            self.client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
            self.from_number = settings.TWILIO_PHONE_NUMBER
            print(f"[Emergency] Twilio Client initialized with from_number: {self.from_number}")
        else:
            self.client = None
            print("[Emergency] WARNING: Twilio credentials NOT found!")

    # ── SMS ──────────────────────────────────────────────────────

    def trigger_sms(self, phone: str, message: str) -> dict:
        """Send an SMS via Twilio. Falls back to console mock if unavailable."""
        if not self.client or not settings.TWILIO_ENABLED:
            print(f"\n--- MOCK SMS ---\nTo: {phone}\n{message}\n----------------\n")
            return {"mode": "mock", "status": "mock_sent"}
        try:
            msg = self.client.messages.create(
                body=message,
                from_=self.from_number,
                to=phone
            )
            print(f"[Emergency] SMS sent to {phone} | SID: {msg.sid}")
            return {"mode": "live", "sid": msg.sid, "status": msg.status}
        except Exception as e:
            print(f"[Emergency] SMS ERROR: {str(e)}")
            print(f"\n--- MOCK SMS FALLBACK ---\nTo: {phone}\n{message}\n-------------------------\n")
            return {"mode": "mock", "status": "mock_fallback", "error": str(e)}

    # ── VOICE CALL ───────────────────────────────────────────────

    def trigger_call(self, phone: str, message: str) -> dict:
        """Place a voice call via Twilio TTS. Falls back to console mock."""
        if not self.client or not settings.TWILIO_ENABLED:
            print(f"\n--- MOCK VOICE CALL ---\nTo: {phone}\n{message}\n-----------------------\n")
            return {"mode": "mock", "status": "mock_call"}
        try:
            twiml = f'<Response><Say voice="alice">{message}</Say></Response>'
            call = self.client.calls.create(
                to=phone,
                from_=self.from_number,
                twiml=twiml
            )
            print(f"[Emergency] Voice call placed to {phone} | SID: {call.sid}")
            return {"mode": "live", "call_sid": call.sid, "status": call.status}
        except Exception as e:
            print(f"[Emergency] VOICE CALL ERROR: {str(e)}")
            print(f"\n--- MOCK VOICE CALL FALLBACK ---\nTo: {phone}\n{message}\n--------------------------------\n")
            return {"mode": "mock", "status": "call_failed", "error": str(e)}

    # ── EMAIL ────────────────────────────────────────────────────

    def send_doctor_email(self, subject: str, body: str) -> dict:
        """
        Send an email to the doctor via SMTP SSL (Gmail).
        Falls back to console mock if not configured.
        """
        if not settings.EMAIL_ENABLED or not settings.SMTP_USERNAME or not settings.SMTP_PASSWORD:
            print(f"\n--- MOCK EMAIL ---\nTo: {settings.DOCTOR_EMAIL}\nSubject: {subject}\n{body}\n------------------\n")
            return {"mode": "mock", "status": "mock_email"}
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

            print(f"[Emergency] Email sent to {settings.DOCTOR_EMAIL}")
            return {"mode": "live", "status": "email_sent"}
        except Exception as e:
            print(f"[Emergency] EMAIL ERROR: {str(e)}")
            print(f"\n--- MOCK EMAIL FALLBACK ---\nTo: {settings.DOCTOR_EMAIL}\nSubject: {subject}\n{body}\n---------------------------\n")
            return {"mode": "mock", "status": "email_fallback", "error": str(e)}


emergency_service = EmergencyService()
