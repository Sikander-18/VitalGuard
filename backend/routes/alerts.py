"""
VitalGuard v2 — Alerts Route
Per-user alerts with escalation and resolution endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
import datetime

from ..db.database import get_db
from ..db import models
from .. import schemas

router = APIRouter()


@router.get("/", response_model=List[schemas.AlertResponse])
async def read_alerts(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    """Get all alerts, newest first."""
    result = await db.execute(
        select(models.Alert)
        .order_by(models.Alert.timestamp.desc())
        .offset(skip)
        .limit(limit)
    )
    alerts = result.scalars().all()
    return list(alerts)


@router.get("/{user_id}", response_model=List[schemas.AlertResponse])
async def read_user_alerts(user_id: str, limit: int = 50, db: AsyncSession = Depends(get_db)):
    """Get alerts for a specific user."""
    result = await db.execute(
        select(models.Alert)
        .where(models.Alert.user_id == user_id)
        .order_by(models.Alert.timestamp.desc())
        .limit(limit)
    )
    alerts = result.scalars().all()
    return list(alerts)


@router.post("/{alert_id}/resolve", response_model=schemas.AlertResponse)
async def resolve_alert(alert_id: int, db: AsyncSession = Depends(get_db)):
    """Mark an alert as resolved."""
    result = await db.execute(select(models.Alert).where(models.Alert.id == alert_id))
    alert = result.scalars().first()
    if alert is None:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.resolved = True
    alert.resolved_at = datetime.datetime.utcnow()
    await db.commit()
    await db.refresh(alert)
    return alert


@router.post("/{alert_id}/escalate", response_model=schemas.AlertResponse)
async def escalate_alert(alert_id: int, db: AsyncSession = Depends(get_db)):
    """Mark an alert as escalated."""
    result = await db.execute(select(models.Alert).where(models.Alert.id == alert_id))
    alert = result.scalars().first()
    if alert is None:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.escalated = True
    await db.commit()
    await db.refresh(alert)
    return alert
