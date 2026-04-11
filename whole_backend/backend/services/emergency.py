import logging
from twilio.rest import Client
from ..config import settings

logger = logging.getLogger(__name__)

class EmergencyService:
    def __init__(self):
        if settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN:
            self.client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
            self.from_number = settings.TWILIO_PHONE_NUMBER
            print(f"[Emergency] Twilio Client initialized with from_number: {self.from_number}")
        else:
            self.client = None
            print("[Emergency] WARNING: Twilio credentials NOT found!")

    def trigger_call(self, phone: str, message: str):
        if not self.client:
            print(f"[Emergency] ERROR: Cannot call {phone}: Twilio client not initialized")
            return
            
        try:
            print(f"[Emergency] Attempting to call {phone}...")
            # We use TwiML to convert text to speech
            twiml = f'<Response><Say voice="alice">{message}</Say></Response>'
            call = self.client.calls.create(
                to=phone,
                from_=self.from_number,
                twiml=twiml
            )
            print(f"[Emergency] SUCCESS! Call SID: {call.sid}")
        except Exception as e:
            print(f"[Emergency] TWILIO ERROR: {str(e)}")

    def trigger_sms(self, phone: str, message: str):
        if not self.client:
            logger.error(f"Cannot SMS {phone}: Twilio client not initialized")
            return
            
        try:
            msg = self.client.messages.create(
                body=message,
                from_=self.from_number,
                to=phone
            )
            logger.info(f"EMERGENCY SMS SID: {msg.sid} sent to {phone}")
        except Exception as e:
            logger.error(f"Twilio SMS Error: {str(e)}")

emergency_service = EmergencyService()
