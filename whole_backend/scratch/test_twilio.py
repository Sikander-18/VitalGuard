import os
from twilio.rest import Client
from backend.config import settings

def test():
    print(f"SID: {settings.TWILIO_ACCOUNT_SID[:5]}...")
    print(f"From: {settings.TWILIO_PHONE_NUMBER}")
    print(f"To: {settings.TWILIO_TARGET_PHONE_NUMBER}")
    
    if not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN:
        print("Error: Missing credentials in settings!")
        return

    client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    try:
        print("Attempting trial call...")
        call = client.calls.create(
            to=settings.TWILIO_TARGET_PHONE_NUMBER,
            from_=settings.TWILIO_PHONE_NUMBER,
            twiml='<Response><Say>Pulse Guard Test Call Success.</Say></Response>'
        )
        print(f"Success! SID: {call.sid}")
    except Exception as e:
        print(f"FAILED: {str(e)}")

if __name__ == "__main__":
    test()
