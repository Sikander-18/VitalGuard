from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve .env relative to whole_backend/ directory
_env_path = Path(__file__).resolve().parent.parent / ".env"

class Settings(BaseSettings):
    # Twilio
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_PHONE_NUMBER: str = ""
    TWILIO_TARGET_PHONE_NUMBER: str = ""
    TWILIO_ENABLED: bool = True

    # Groq AI
    GROQ_API_KEY: str = ""

    # Patient
    PATIENT_NAME: str = "Patient"
    PATIENT_PHONE: str = ""

    # Emergency Contact
    EMERGENCY_CONTACT_NAME: str = "Emergency Contact"
    EMERGENCY_CONTACT_PHONE: str = ""

    # Doctor Email (SMTP)
    DOCTOR_EMAIL: str = ""
    EMAIL_ENABLED: bool = False
    SMTP_SERVER: str = "smtp.gmail.com"
    SMTP_PORT: int = 465
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""

    model_config = SettingsConfigDict(env_file=str(_env_path))

settings = Settings()

# Debug: Verify settings are loaded
print(f"--- CONFIG STARTUP ---")
print(f"Account SID: {settings.TWILIO_ACCOUNT_SID[:5]}... (Len: {len(settings.TWILIO_ACCOUNT_SID)})")
print(f"Target Phone: {settings.TWILIO_TARGET_PHONE_NUMBER}")
print(f"Groq API Key set: {bool(settings.GROQ_API_KEY)}")
print(f"-----------------------")
