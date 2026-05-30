from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
import logging

from ..db.database import get_db

router = APIRouter()
logger = logging.getLogger("vitalguard.routes.notifications")

class TokenRegistration(BaseModel):
    user_id: str
    token: str

class SendPushRequest(BaseModel):
    user_id: str
    title: str
    body: str
    severity: str  # LOW | FUTURE_ALERT | CRITICAL

# Cache FCM tokens in memory for demonstration purposes
FCM_TOKENS = {}

@router.post("/register-token")
async def register_token(data: TokenRegistration):
    """Register client FCM push token associated with their User ID."""
    FCM_TOKENS[data.user_id] = data.token
    logger.info(f"FCM token registered for patient {data.user_id}: {data.token[:12]}...")
    return {"success": True, "message": "Token registered successfully"}

@router.post("/send")
async def send_push(data: SendPushRequest):
    """Send push notification logic shell."""
    token = FCM_TOKENS.get(data.user_id)
    if not token:
        logger.warning(f"No FCM token registered for patient {data.user_id} — falling back to in-app/desktop push")
        return {"success": False, "message": "No token registered"}
        
    logger.info(f"FCM push notification triggered for {data.user_id}: [{data.title}] - {data.body}")
    
    # Optional FCM Admin SDK push logic here:
    # try:
    #     import firebase_admin
    #     from firebase_admin import messaging
    #     message = messaging.Message(
    #         notification=messaging.Notification(title=data.title, body=data.body),
    #         token=token
    #     )
    #     messaging.send(message)
    # except Exception as e:
    #     logger.warning(f"FCM Admin SDK push failed (expected in local dev environment): {e}")
        
    return {"success": True, "message": f"Push notification triggered successfully for token: {token[:12]}..."}
