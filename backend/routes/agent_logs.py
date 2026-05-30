"""
VitalGuard v2 — Agent Logs Route
Endpoint for retrieving agent pipeline execution traces.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List

from ..db.database import get_db
from ..db import models
from .. import schemas

router = APIRouter()


@router.get("/{user_id}", response_model=List[schemas.AgentLogResponse])
async def get_agent_logs(user_id: str, limit: int = 20, db: AsyncSession = Depends(get_db)):
    """Get agent pipeline execution history for a user."""
    result = await db.execute(
        select(models.AgentLog)
        .where(models.AgentLog.user_id == user_id)
        .order_by(models.AgentLog.timestamp.desc())
        .limit(limit)
    )
    logs = result.scalars().all()
    return list(logs)


@router.get("/{user_id}/latest", response_model=schemas.AgentLogResponse)
async def get_latest_agent_log(user_id: str, db: AsyncSession = Depends(get_db)):
    """Get the most recent agent pipeline trace for a user."""
    result = await db.execute(
        select(models.AgentLog)
        .where(models.AgentLog.user_id == user_id)
        .order_by(models.AgentLog.timestamp.desc())
        .limit(1)
    )
    log = result.scalars().first()
    if log is None:
        return schemas.AgentLogResponse(
            id=0, user_id=user_id,
            timestamp=__import__("datetime").datetime.utcnow(),
            agent_output='{"message": "No agent logs yet"}',
        )
    return log
