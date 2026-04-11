from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
from ..db.database import get_db
from ..db import models
from .. import schemas
from ..services.websocket import manager
from ..engine.rule_engine import check_vitals_anomaly
from ..agents.graph import agent_graph
import json

router = APIRouter()

@router.post("/", response_model=schemas.VitalResponse)
async def create_vital(vital: schemas.VitalCreate, db: AsyncSession = Depends(get_db)):
    vital_dict = vital.model_dump()
    
    # 0. Fetch User Profile for context (location, contacts, etc.)
    user_result = await db.execute(select(models.User).where(models.User.id == vital.user_id))
    user_profile = user_result.scalars().first()
    emergency_contacts = user_profile.emergency_contacts if user_profile else "[]"

    # 1. Rule Engine
    if check_vitals_anomaly(vital_dict):
        # 2. Trigger LangGraph Agent
        state = {
            "vitals": vital_dict,
            "user_id": vital.user_id,
            "emergency_contacts": emergency_contacts,
            "condition": None,
            "severity": None,
            "reasoning": None
        }
        # In a real async app we'd await the agent execution if it's an async graph,
        # but LangGraph compiles to sync unless specifically set.
        final_state = agent_graph.invoke(state)
        
        vital.condition = final_state.get("condition", "normal")
        vital.severity = final_state.get("severity", "low")
        vital.reasoning = final_state.get("reasoning", "")
        vital.actions = json.dumps(final_state.get("actions", []))
        
        # If critical, we would also trigger emergency service or create an Alert
        if vital.condition in ["critical", "future_alert"]:
            alert = models.Alert(
                user_id=vital.user_id,
                condition=vital.condition,
                vitals_snapshot=json.dumps(vital_dict)
            )
            db.add(alert)
    else:
        vital.condition = "normal"

    db_vital = models.Vital(**vital.model_dump())
    db.add(db_vital)
    await db.commit()
    await db.refresh(db_vital)
    
    # Broadcast to frontend
    vital_data = schemas.VitalResponse.model_validate(db_vital)
    # JSON serializable format with stringified datetime
    vital_json = vital_data.model_dump_json()
    await manager.send_personal_message(vital_json, vital.user_id)
    # Also broadcast for testing/admin purposes
    await manager.broadcast(vital_json)
    
    return db_vital

@router.get("/{user_id}", response_model=List[schemas.VitalResponse])
async def read_vitals(user_id: str, db: AsyncSession = Depends(get_db), limit: int = 30):
    result = await db.execute(select(models.Vital).where(models.Vital.user_id == user_id).order_by(models.Vital.timestamp.desc()).limit(limit))
    vitals = result.scalars().all()
    # Return reversed to get chronological order from oldest to newest in the sample
    return list(reversed(vitals))
