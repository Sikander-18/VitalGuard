"""
VitalGuard v2 — Configuration
Loads environment variables from server/.env
"""

import logging
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

_env_path = Path(__file__).resolve().parents[1] / ".env"

logger = logging.getLogger("vitalguard.config")


class Settings(BaseSettings):
    # ── Twilio ────────────────────────────────────────────────────
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_PHONE_NUMBER: str = ""
    TWILIO_TARGET_PHONE_NUMBER: str = ""
    TWILIO_ENABLED: bool = True

    # ── Groq AI ───────────────────────────────────────────────────
    GROQ_API_KEY: str = ""

    # ── Patient ───────────────────────────────────────────────────
    PATIENT_NAME: str = "Patient"
    PATIENT_PHONE: str = ""

    # ── Emergency Contact ─────────────────────────────────────────
    EMERGENCY_CONTACT_NAME: str = "Emergency Contact"
    EMERGENCY_CONTACT_PHONE: str = ""

    # ── Doctor Email / SMTP ───────────────────────────────────────
    DOCTOR_EMAIL: str = ""
    EMAIL_ENABLED: bool = False
    SMTP_SERVER: str = "smtp.gmail.com"
    SMTP_PORT: int = 465
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""

    # ── Agent Pipeline ────────────────────────────────────────────
    AGENT_TIMEOUT_SECONDS: int = 25
    VITALS_INTERVAL_SECONDS: int = 3
    LLM_MODEL: str = "llama-3.3-70b-versatile"
    LLM_TEMPERATURE: float = 0.1

    # ── Location (optional) ───────────────────────────────────────
    LOCATION_API_KEY: str = ""

    model_config = SettingsConfigDict(env_file=str(_env_path), extra="ignore")


settings = Settings()

# Startup logging
logger.info(f"Groq API Key set: {bool(settings.GROQ_API_KEY)}")
logger.info(f"Twilio enabled: {settings.TWILIO_ENABLED}")
logger.info(f"Email enabled: {settings.EMAIL_ENABLED}")
