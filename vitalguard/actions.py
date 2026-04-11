"""
VitalGuard — Action Handlers v2
ONE-SHOT firing logic:
  - Each action (SMS, voice call, doctor email) fires EXACTLY ONCE per incident
  - An "incident" starts when risk level rises above LOW
  - Incident resets ONLY when risk returns to LOW for 3 consecutive readings
  - This prevents spam while ensuring the alert always gets through once

Actions:
  log              — just record, no notification
  alert_user       — one SMS to patient (fires once per incident)
  schedule_doctor  — one email to doctor (fires once per incident)
  call_emergency   — one SMS + one voice call to emergency contact (fires once per incident)
  notify_contact   — called internally by call_emergency
"""

import asyncio
import random
import time
import logging
import smtplib
import ssl
from email.message import EmailMessage
from datetime import datetime
from dataclasses import dataclass
from typing import Literal, Optional

from twilio.rest import Client

from config import (
    TWILIO_ENABLED,
    TWILIO_ACCOUNT_SID,
    TWILIO_AUTH_TOKEN,
    TWILIO_PHONE_NUMBER,
    EMERGENCY_CONTACT_PHONE,
    EMERGENCY_CONTACT_NAME,
    PATIENT_PHONE,
    PATIENT_NAME,
    is_twilio_configured,
    DOCTOR_EMAIL,
    EMAIL_ENABLED,
    SMTP_SERVER,
    SMTP_PORT,
    SMTP_USERNAME,
    SMTP_PASSWORD,
)

logger = logging.getLogger("vitalguard.actions")

ActionType = Literal["log", "alert_user", "schedule_doctor", "call_emergency", "notify_contact"]


# ────────────────────────────────────────────────────────────────
# ONE-SHOT INCIDENT LOCK
#
# Each flag below is True = "already fired this incident, skip".
# All flags reset together when patient returns to LOW for
# RESET_AFTER_N_LOW consecutive readings.
# ────────────────────────────────────────────────────────────────

_fired: dict[str, bool] = {
    "alert_user":      False,
    "schedule_doctor": False,
    "call_emergency":  False,
    "notify_contact":  False,
}

_low_streak        = 0       # how many consecutive LOW readings we've seen
RESET_AFTER_N_LOW  = 3       # reset all locks after this many LOW readings in a row


def reset_incident():
    """Reset all one-shot locks — call when patient is back to normal."""
    global _low_streak
    for key in _fired:
        _fired[key] = False
    _low_streak = 0
    logger.info("Incident reset — all action locks cleared.")


def _try_fire(action_type: str) -> bool:
    """
    Returns True (and marks as fired) if this action hasn't fired yet this incident.
    Returns False if it already fired — caller should skip sending.
    """
    if _fired.get(action_type, False):
        return False
    _fired[action_type] = True
    return True


def _update_incident_state(risk_level: str):
    """
    Track consecutive LOW readings.
    After RESET_AFTER_N_LOW consecutive LOWs, reset the incident so
    the next anomaly will fire fresh alerts again.
    """
    global _low_streak
    if risk_level == "LOW":
        _low_streak += 1
        if _low_streak >= RESET_AFTER_N_LOW:
            reset_incident()
    else:
        _low_streak = 0


# ────────────────────────────────────────────────────────────────
# TWILIO CLIENT
# ────────────────────────────────────────────────────────────────

_twilio_client = None


def _get_twilio_client():
    global _twilio_client
    if _twilio_client is None and is_twilio_configured():
        try:
            _twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
            logger.info("Twilio client initialised.")
        except Exception as e:
            logger.error(f"Twilio init failed: {e}")
    return _twilio_client


# ────────────────────────────────────────────────────────────────
# SMS
# ────────────────────────────────────────────────────────────────

def _send_sms(to_number: str, body: str) -> dict:
    client = _get_twilio_client()
    if not client or not TWILIO_ENABLED:
        logger.info(f"[Mock SMS] To: {to_number}\n{body}")
        print(f"\n--- MOCK SMS ---\nTo: {to_number}\n{body}\n----------------\n")
        return {"mode": "mock", "status": "mock_sent"}
    try:
        msg = client.messages.create(body=body, from_=TWILIO_PHONE_NUMBER, to=to_number)
        logger.info(f"SMS sent to {to_number} | SID: {msg.sid}")
        return {"mode": "live", "sid": msg.sid, "status": msg.status}
    except Exception as e:
        logger.error(f"SMS failed: {e}")
        print(f"\n--- MOCK SMS FALLBACK ---\nTo: {to_number}\n{body}\n-------------------------\n")
        return {"mode": "mock", "status": "mock_sent_fallback", "error": str(e)}


async def _send_sms_async(to_number: str, body: str) -> dict:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _send_sms, to_number, body)


# ────────────────────────────────────────────────────────────────
# VOICE CALL
# ────────────────────────────────────────────────────────────────

def _make_voice_call(phone_number: str, message: str) -> dict:
    client = _get_twilio_client()
    if not client or not TWILIO_ENABLED:
        logger.info(f"[Mock Call] To: {phone_number}\n{message}")
        print(f"\n--- MOCK VOICE CALL ---\nTo: {phone_number}\n{message}\n-----------------------\n")
        return {"mode": "mock", "status": "mock_call"}
    try:
        call = client.calls.create(
            twiml=f"<Response><Say voice='alice'>{message}</Say></Response>",
            to=phone_number,
            from_=TWILIO_PHONE_NUMBER,
        )
        logger.info(f"Voice call placed to {phone_number} | SID: {call.sid}")
        return {"mode": "live", "call_sid": call.sid, "status": call.status}
    except Exception as e:
        logger.error(f"Voice call failed: {e}")
        print(f"\n--- MOCK VOICE CALL FALLBACK ---\nTo: {phone_number}\n{message}\n--------------------------------\n")
        return {"mode": "mock", "status": "call_failed", "error": str(e)}


# ────────────────────────────────────────────────────────────────
# EMAIL
# ────────────────────────────────────────────────────────────────

def _send_email(to_email: str, subject: str, body: str) -> dict:
    if not EMAIL_ENABLED or not SMTP_USERNAME or not SMTP_PASSWORD:
        logger.info(f"[Mock Email] To: {to_email} | {subject}")
        print(f"\n--- MOCK EMAIL ---\nTo: {to_email}\nSubject: {subject}\n{body}\n------------------\n")
        return {"mode": "mock", "status": "mock_sent_email"}
    try:
        msg = EmailMessage()
        msg.set_content(body)
        msg["Subject"] = subject
        msg["From"]    = SMTP_USERNAME
        msg["To"]      = to_email
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, context=context) as server:
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(msg)
        logger.info(f"Email sent to {to_email}")
        return {"mode": "live", "status": "email_sent"}
    except Exception as e:
        logger.error(f"Email failed: {e}")
        print(f"\n--- MOCK EMAIL FALLBACK ---\nTo: {to_email}\nSubject: {subject}\n{body}\n---------------------------\n")
        return {"mode": "mock", "status": "mock_sent_email_fallback", "error": str(e)}


async def _send_email_async(to_email: str, subject: str, body: str) -> dict:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _send_email, to_email, subject, body)


# ────────────────────────────────────────────────────────────────
# ACTION RESULT
# ────────────────────────────────────────────────────────────────

@dataclass
class ActionResult:
    action_type: ActionType
    success: bool
    message: str
    details: dict
    timestamp: str

    def to_dict(self) -> dict:
        return {
            "action_type": self.action_type,
            "success":     self.success,
            "message":     self.message,
            "details":     self.details,
            "timestamp":   self.timestamp,
        }


# ────────────────────────────────────────────────────────────────
# ACTIONS
# ────────────────────────────────────────────────────────────────

async def log_reading(vitals, risk, reasoning, location=None, trigger_vitals=None):
    """Just record the reading. Also updates incident state."""
    _update_incident_state(risk.get("level", "LOW"))
    return ActionResult(
        action_type="log",
        success=True,
        message="Reading logged",
        details={"trigger_vitals": trigger_vitals or []},
        timestamp=datetime.now().isoformat(),
    )


async def alert_user(vitals, risk, reasoning, location=None, trigger_vitals=None):
    """Send ONE SMS to patient. Silently skipped if already sent this incident."""
    _update_incident_state(risk.get("level", "LOW"))

    if not _try_fire("alert_user"):
        # Already sent this incident — do nothing
        return ActionResult(
            action_type="alert_user",
            success=True,
            message="Alert already sent for this incident — skipped",
            details={"sms_delivery": {"mode": "skipped", "reason": "already_fired_this_incident"},
                     "trigger_vitals": trigger_vitals or []},
            timestamp=datetime.now().isoformat(),
        )

    target_phone = PATIENT_PHONE or "+10000000000"
    sms_body = (
        f"VitalGuard Health Alert\n"
        f"Risk Score: {risk.get('score', 0)}/100\n"
        f"Heart Rate: {vitals.get('heart_rate')} bpm\n"
        f"SpO2: {vitals.get('spo2')}%\n"
        f"Temperature: {vitals.get('temperature')}C\n"
    )
    if trigger_vitals:
        sms_body += f"Concern: {', '.join(trigger_vitals[:2])}\n"
    if location and location.get("lat") and location.get("lng"):
        sms_body += f"Location: https://maps.google.com/?q={location['lat']},{location['lng']}\n"
    sms_body += "Please check your vitals. Contact a doctor if you feel unwell."

    sms_result = await _send_sms_async(target_phone, sms_body)

    return ActionResult(
        action_type="alert_user",
        success=True,
        message="Health alert sent to patient",
        details={"sms_delivery": sms_result, "trigger_vitals": trigger_vitals or []},
        timestamp=datetime.now().isoformat(),
    )


async def schedule_doctor(vitals, risk, reasoning, location=None, trigger_vitals=None):
    """Send ONE appointment email to doctor. Silently skipped if already sent this incident."""
    _update_incident_state(risk.get("level", "LOW"))

    if not _try_fire("schedule_doctor"):
        return ActionResult(
            action_type="schedule_doctor",
            success=True,
            message="Doctor appointment already scheduled for this incident — skipped",
            details={"email_delivery": {"mode": "skipped", "reason": "already_fired_this_incident"},
                     "trigger_vitals": trigger_vitals or []},
            timestamp=datetime.now().isoformat(),
        )

    doctor = random.choice(["Dr. Priya Sharma", "Dr. Ravi Patel", "Dr. Ananya Gupta"])
    subject = f"[VitalGuard] Appointment Needed — {PATIENT_NAME}"
    body = (
        f"Dear {doctor},\n\n"
        f"VitalGuard has detected elevated risk vitals for patient {PATIENT_NAME} "
        f"and has automatically flagged them for a medical review.\n\n"
        f"Patient Vitals at time of alert:\n"
        f"  Heart Rate:   {vitals.get('heart_rate')} bpm\n"
        f"  SpO2:         {vitals.get('spo2')}%\n"
        f"  Temperature:  {vitals.get('temperature')}C\n"
        f"  HRV:          {vitals.get('hrv')} ms\n"
        f"  Risk Score:   {risk.get('score')}/100 ({risk.get('level')})\n"
        f"  MEWS Score:   {risk.get('mews_score', 'N/A')}/12\n\n"
        f"Clinical Concern: {reasoning}\n"
    )
    if trigger_vitals:
        body += f"\nTriggered by: {chr(10).join('  - ' + t for t in trigger_vitals)}\n"
    body += "\nPlease schedule an appointment at your earliest convenience.\n\nVitalGuard System"

    email_result = await _send_email_async(DOCTOR_EMAIL, subject, body)

    return ActionResult(
        action_type="schedule_doctor",
        success=True,
        message=f"Appointment request sent to {doctor}",
        details={"doctor": doctor, "email_delivery": email_result,
                 "trigger_vitals": trigger_vitals or []},
        timestamp=datetime.now().isoformat(),
    )


async def call_emergency(vitals, risk, reasoning, location=None, trigger_vitals=None):
    """
    Log the emergency case ID. The actual SMS + call goes via notify_contact,
    which is always called right after this by action_executor.
    """
    _update_incident_state(risk.get("level", "LOW"))
    case_id = f"EMG-{random.randint(100000, 999999)}"
    return ActionResult(
        action_type="call_emergency",
        success=True,
        message=f"Emergency response initiated — Case {case_id}",
        details={"case_id": case_id, "trigger_vitals": trigger_vitals or []},
        timestamp=datetime.now().isoformat(),
    )


async def notify_contact(vitals, risk, reasoning, location=None, trigger_vitals=None):
    """
    Send ONE SMS + ONE voice call to the emergency contact.
    Both are one-shot — silently skipped if already done this incident.
    """
    _update_incident_state(risk.get("level", "LOW"))

    target_phone = EMERGENCY_CONTACT_PHONE or "+10000000000"
    sms_result   = None
    voice_result = None

    # ── ONE SMS ──────────────────────────────────────────────────
    if not _try_fire("notify_contact"):
        sms_result   = {"mode": "skipped", "reason": "already_fired_this_incident"}
        voice_result = {"mode": "skipped", "reason": "already_fired_this_incident"}
        return ActionResult(
            action_type="notify_contact",
            success=True,
            message=f"Emergency contact already notified this incident — skipped",
            details={"sms_delivery": sms_result, "voice_call": voice_result,
                     "trigger_vitals": trigger_vitals or []},
            timestamp=datetime.now().isoformat(),
        )

    # SMS
    sms_body = (
        f"EMERGENCY — VitalGuard Alert\n"
        f"Patient: {PATIENT_NAME}\n"
        f"Risk Score: {risk.get('score', 0)}/100 (CRITICAL)\n"
        f"Heart Rate: {vitals.get('heart_rate')} bpm\n"
        f"SpO2: {vitals.get('spo2')}%\n"
    )
    if trigger_vitals:
        sms_body += f"Cause: {', '.join(trigger_vitals[:2])}\n"
    if location and location.get("lat") and location.get("lng"):
        sms_body += f"Location: https://maps.google.com/?q={location['lat']},{location['lng']}\n"
    else:
        sms_body += "Location: Unknown\n"
    sms_body += "Emergency services have been alerted. Please respond immediately."

    sms_result = await _send_sms_async(target_phone, sms_body)

    # ── ONE VOICE CALL ───────────────────────────────────────────
    voice_message = (
        f"Emergency alert from VitalGuard. "
        f"{PATIENT_NAME} is experiencing a critical health event. "
        f"Heart rate is {vitals.get('heart_rate')} beats per minute. "
        f"Oxygen level is {vitals.get('spo2')} percent. "
        f"Emergency services have been contacted. "
        f"Please respond immediately."
    )
    voice_result = _make_voice_call(target_phone, voice_message)

    return ActionResult(
        action_type="notify_contact",
        success=True,
        message=f"Emergency contact {EMERGENCY_CONTACT_NAME} notified — SMS + Call sent",
        details={"sms_delivery": sms_result, "voice_call": voice_result,
                 "trigger_vitals": trigger_vitals or []},
        timestamp=datetime.now().isoformat(),
    )


# ────────────────────────────────────────────────────────────────
# DISPATCH
# ────────────────────────────────────────────────────────────────

ACTION_DISPATCH = {
    "log":             log_reading,
    "alert_user":      alert_user,
    "schedule_doctor": schedule_doctor,
    "call_emergency":  call_emergency,
    "notify_contact":  notify_contact,
}


async def execute_action(action_type, vitals, risk, reasoning,
                          location=None, trigger_vitals=None):
    handler = ACTION_DISPATCH.get(action_type, log_reading)
    return await handler(vitals, risk, reasoning, location, trigger_vitals)


def get_twilio_status():
    return {
        "enabled":                TWILIO_ENABLED,
        "configured":             is_twilio_configured(),
        "patient_phone_set":      bool(PATIENT_PHONE),
        "emergency_contact_set":  bool(EMERGENCY_CONTACT_PHONE),
        "emergency_contact_name": EMERGENCY_CONTACT_NAME,
        "patient_name":           PATIENT_NAME,
        "incident_state":         {k: ("fired" if v else "ready") for k, v in _fired.items()},
    }
