from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
from ..db.database import get_db
from ..db import models
from .. import schemas

router = APIRouter()

@router.get("/", response_model=List[schemas.AlertResponse])
async def read_alerts(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.Alert).order_by(models.Alert.timestamp.desc()).offset(skip).limit(limit))
    alerts = result.scalars().all()
    return list(alerts)

@router.post("/{alert_id}/resolve", response_model=schemas.AlertResponse)
async def resolve_alert(alert_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.Alert).where(models.Alert.id == alert_id))
    alert = result.scalars().first()
    if alert:
        alert.resolved = 1
        await db.commit()
        await db.refresh(alert)
    return alert
