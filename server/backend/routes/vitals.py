"""
VitalGuard v2 — Vitals Route
Full pipeline: Rule Engine → Agent → DB → WebSocket → Alert creation
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from datetime import datetime, timedelta
from typing import List
import json
import time
import logging

from ..db.database import get_db
from ..db import models
from .. import schemas
from ..services.websocket import manager
from ..engine.rule_engine import compute_risk, check_vitals_anomaly
from ..agents.graph import agent_graph

logger = logging.getLogger("vitalguard.routes.vitals")

router = APIRouter()


@router.post("/", response_model=schemas.VitalResponse)
async def create_vital(vital: schemas.VitalCreate, db: AsyncSession = Depends(get_db)):
    """
    Ingest a vital sign reading through the full pipeline:
    1. Data validation
    2. Rule engine (MEWS + trend analysis)
    3. LangGraph agent pipeline (if anomaly detected)
    4. Store to DB
    5. Create alert if needed
    6. WebSocket broadcast
    """
    vital_dict = vital.model_dump()
    start_time = time.time()

    # Normalize: Remove all explicit Nones to secure agent pipeline
    if vital_dict.get("heart_rate") is None:
        vital_dict["heart_rate"] = float(vital_dict.get("bpm") or 0)
    if vital_dict.get("bpm") is None:
        vital_dict["bpm"] = int(vital_dict.get("heart_rate") or 0)
    if vital_dict.get("spo2") is None: vital_dict["spo2"] = 0
    if vital_dict.get("temperature") is None: vital_dict["temperature"] = 36.6
    if vital_dict.get("hrv") is None: vital_dict["hrv"] = 40.0
    if vital_dict.get("systolic") is None: vital_dict["systolic"] = 120
    if vital_dict.get("diastolic") is None: vital_dict["diastolic"] = 80

    # 0. Fetch User Profile
    user_result = await db.execute(
        select(models.User).where(models.User.id == vital.user_id)
    )
    user_profile = user_result.scalars().first()
    emergency_contacts = user_profile.emergency_contacts if user_profile else "[]"

    # Fetch patient baseline
    profile_result = await db.execute(
        select(models.PatientProfile).where(models.PatientProfile.user_id == vital.user_id)
    )
    patient_profile = profile_result.scalars().first()
    patient_history = {}
    if patient_profile:
        patient_history = {
            "baseline_hr": patient_profile.baseline_hr,
            "baseline_spo2": patient_profile.baseline_spo2,
            "baseline_temp": patient_profile.baseline_temp,
            "baseline_hrv": patient_profile.baseline_hrv,
            "conditions": patient_profile.conditions,
            "medications": patient_profile.medications,
        }

    # 1. Rule Engine
    risk_assessment = compute_risk(vital_dict, patient_id=vital.user_id)
    risk_dict = risk_assessment.to_dict()

    # 2. Agent Pipeline (if anomaly detected OR risk > LOW)
    if check_vitals_anomaly(vital_dict) or risk_assessment.score > 30:
        try:
            state = {
                "vitals": vital_dict,
                "risk_assessment": risk_dict,
                "patient_history": patient_history,
                "location": {
                    "lat": user_profile.location_lat if user_profile else None,
                    "lng": user_profile.location_lng if user_profile else None,
                },
                "user_id": vital.user_id,
                "emergency_contacts": emergency_contacts,
                # Agent output fields (initialized empty)
                "vitals_interpretation": "",
                "prediction": {},
                "risk_classification": {},
                "decided_action": "",
                "action_reasoning": "",
                "patient_message": "",
                "doctor_message": "",
                "explainability_trace": [],
                "action_result": {},
                "full_log": {},
                "condition": None,
                "severity": None,
                "reasoning": None,
                "actions": None,
            }

            final_state = await agent_graph.ainvoke(state)

            vital.condition = final_state.get("condition", "normal")
            vital.severity = final_state.get("severity", "low")
            vital.reasoning = final_state.get("reasoning", "")
            actions_list = final_state.get("actions", [])
            vital.actions = json.dumps(actions_list) if isinstance(actions_list, list) else str(actions_list)

            # Save agent log
            duration_ms = int((time.time() - start_time) * 1000)
            agent_log = models.AgentLog(
                user_id=vital.user_id,
                vitals_snapshot=json.dumps(vital_dict),
                risk_input=json.dumps(risk_dict),
                agent_output=json.dumps(final_state.get("full_log", {}), default=str),
                trace=json.dumps(final_state.get("explainability_trace", []), default=str),
                duration_ms=duration_ms,
            )
            db.add(agent_log)

            # Create alert if non-normal
            if vital.condition in ("critical", "future_alert"):
                alert = models.Alert(
                    user_id=vital.user_id,
                    risk_level=risk_dict.get("level", "LOW"),
                    risk_score=risk_dict.get("score", 0),
                    mews_score=risk_dict.get("mews_score", 0),
                    contributing_factors=json.dumps(risk_dict.get("contributing_factors", [])),
                    ai_summary=final_state.get("vitals_interpretation", ""),
                    decided_action=final_state.get("decided_action", "log"),
                    action_result=json.dumps(final_state.get("action_result", {}), default=str),
                    condition=vital.condition,
                    vitals_snapshot=json.dumps(vital_dict),
                )
                db.add(alert)

        except Exception as e:
            logger.error(f"Agent pipeline error: {e}")
            vital.condition = "normal"
            vital.severity = "low"
            vital.reasoning = f"Agent error: {str(e)}"
    else:
        vital.condition = "normal"
        vital.severity = "low"

    # 3. Save vital to DB
    db_vital = models.Vital(**vital.model_dump())
    db_vital.heart_rate = vital_dict.get("heart_rate")
    db_vital.temperature = vital_dict.get("temperature", 36.6)
    db.add(db_vital)
    await db.commit()
    await db.refresh(db_vital)

    # 4. WebSocket broadcast
    try:
        vital_data = schemas.VitalResponse.model_validate(db_vital)
        ws_payload = vital_data.model_dump_json()
        await manager.send_personal_message(ws_payload, vital.user_id)
        await manager.broadcast(ws_payload)
    except Exception as e:
        logger.warning(f"WebSocket broadcast failed: {e}")

    return db_vital


@router.get("/{user_id}", response_model=List[schemas.VitalResponse])
async def read_vitals(user_id: str, limit: int = 30, db: AsyncSession = Depends(get_db)):
    """Get vital sign history for a user."""
    result = await db.execute(
        select(models.Vital)
        .where(models.Vital.user_id == user_id)
        .order_by(models.Vital.timestamp.desc())
        .limit(limit)
    )
    vitals = result.scalars().all()
    return list(reversed(vitals))


@router.get("/{user_id}/trends")
async def get_vital_trends(user_id: str, range: str = "realtime", db: AsyncSession = Depends(get_db)):
    """
    Get aggregated vital trends:
    - realtime: Last 30 raw readings (sliding window)
    - day: Last 24 hours aggregated hourly
    - week: Last 7 days aggregated daily
    - month: Last 30 days aggregated daily
    """
    now = datetime.utcnow()
    
    if range == "realtime":
        result = await db.execute(
            select(models.Vital)
            .where(models.Vital.user_id == user_id)
            .order_by(models.Vital.timestamp.desc())
            .limit(30)
        )
        vitals = result.scalars().all()
        # Return as raw dicts mapping schemas.VitalResponse structure
        return [{
            "id": v.id,
            "user_id": v.user_id,
            "timestamp": v.timestamp,
            "heart_rate": v.heart_rate,
            "spo2": v.spo2,
            "temperature": v.temperature,
            "hrv": v.hrv,
            "systolic": v.systolic,
            "diastolic": v.diastolic,
            "source": v.source,
            "bpm": v.bpm,
            "condition": v.condition,
            "severity": v.severity,
            "reasoning": v.reasoning,
            "actions": v.actions,
            "raw_json": v.raw_json
        } for v in reversed(vitals)]
        
    elif range == "day":
        cutoff = now - timedelta(hours=24)
        group_by_format = "%Y-%m-%d %H:00:00"
    elif range == "week":
        cutoff = now - timedelta(days=7)
        group_by_format = "%Y-%m-%d"
    elif range == "month":
        cutoff = now - timedelta(days=30)
        group_by_format = "%Y-%m-%d"
    else:
        cutoff = now - timedelta(days=7)
        group_by_format = "%Y-%m-%d"

    stmt = (
        select(
            func.strftime(group_by_format, models.Vital.timestamp).label("time_bucket"),
            func.avg(models.Vital.heart_rate).label("avg_hr"),
            func.avg(models.Vital.spo2).label("avg_spo2"),
            func.avg(models.Vital.systolic).label("avg_sys"),
            func.avg(models.Vital.diastolic).label("avg_dia"),
            func.avg(models.Vital.hrv).label("avg_hrv"),
            func.avg(models.Vital.temperature).label("avg_temp")
        )
        .where(models.Vital.user_id == user_id)
        .where(models.Vital.timestamp >= cutoff)
        .group_by("time_bucket")
        .order_by("time_bucket")
    )
    
    result = await db.execute(stmt)
    rows = result.all()
    
    trends = []
    for r in rows:
        trends.append({
            "timestamp": r.time_bucket,
            "heart_rate": round(r.avg_hr, 1) if r.avg_hr else 0.0,
            "spo2": round(r.avg_spo2, 1) if r.avg_spo2 else 0.0,
            "systolic": int(r.avg_sys) if r.avg_sys else 0,
            "diastolic": int(r.avg_dia) if r.avg_dia else 0,
            "hrv": round(r.avg_hrv, 1) if r.avg_hrv else 0.0,
            "temperature": round(r.avg_temp, 1) if r.avg_temp else 36.6,
            "user_id": user_id,
            "source": "aggregated"
        })
        
    return trends
