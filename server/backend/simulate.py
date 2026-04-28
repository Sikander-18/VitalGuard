"""
VitalGuard v2 — Clinical-Grade Vital Signs Simulator
MIMIC-III derived distributions with circadian rhythm, temporal drift,
correlated vitals, and scenario-based presets.

Supports:
  - Patient archetypes (healthy, elderly, cardiac, post-op)
  - Simulation modes: normal, mild_anomaly, critical, auto
  - Multi-patient via simulator registry
  - Full pipeline integration (Rule Engine → Agent → DB → WS)
"""

import random
import math
import json
from enum import Enum
from typing import Optional, Dict
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from .db.database import get_db
from .db import models
from .schemas import VitalCreate
from .routes.vitals import create_vital

router = APIRouter()


# ── Patient Profiles (MIMIC-III derived) ──────────────────────────

PATIENT_PROFILES = {
    "healthy_adult": {
        "hr_base": 72, "hr_std": 8,
        "spo2_base": 98.2, "spo2_std": 0.5,
        "temp_base": 36.6, "temp_std": 0.2,
        "hrv_base": 48, "hrv_std": 10,
        "sys_base": 118, "dia_base": 76,
        "label": "Healthy Adult (28 F)",
    },
    "elderly_patient": {
        "hr_base": 78, "hr_std": 10,
        "spo2_base": 96.5, "spo2_std": 1.0,
        "temp_base": 36.4, "temp_std": 0.25,
        "hrv_base": 28, "hrv_std": 7,
        "sys_base": 138, "dia_base": 82,
        "label": "Elderly (74 M, HTN)",
    },
    "cardiac_patient": {
        "hr_base": 88, "hr_std": 15,
        "spo2_base": 95.8, "spo2_std": 1.5,
        "temp_base": 36.7, "temp_std": 0.3,
        "hrv_base": 18, "hrv_std": 5,
        "sys_base": 145, "dia_base": 92,
        "label": "Cardiac (61 M, CHF)",
    },
    "post_op": {
        "hr_base": 82, "hr_std": 12,
        "spo2_base": 97.0, "spo2_std": 1.2,
        "temp_base": 37.2, "temp_std": 0.4,
        "hrv_base": 22, "hrv_std": 6,
        "sys_base": 125, "dia_base": 78,
        "label": "Post-Op (45 F, Day 1)",
    },
}

# MIMIC-III scenario parameters
MIMIC_NORMAL = {"hr": 80, "spo2": 97.9, "temp": 36.8, "hrv": 42, "sys": 120, "dia": 78}
MIMIC_MILD = {"hr": 108, "spo2": 94.2, "temp": 38.6, "hrv": 16, "sys": 148, "dia": 95}
MIMIC_CRITICAL_SEPSIS = {"hr": 138, "spo2": 84.5, "temp": 39.8, "hrv": 6.5, "sys": 85, "dia": 55}
MIMIC_CRITICAL_CARDIAC = {"hr": 155, "spo2": 87.0, "temp": 37.2, "hrv": 5, "sys": 195, "dia": 115}


# ── Circadian Rhythm ──────────────────────────────────────────────

def _circadian_offset(hour: Optional[float] = None) -> dict:
    if hour is None:
        hour = datetime.now().hour + datetime.now().minute / 60
    return {
        "hr": 5.0 * math.sin(2 * math.pi * (hour - 3) / 24),
        "temp": 0.4 * math.sin(2 * math.pi * (hour - 4) / 24),
    }


def _noise(value: float, std: float) -> float:
    return value + random.gauss(0, std)


# ── Scenario Enum ─────────────────────────────────────────────────

class ScenarioType(str, Enum):
    NORMAL = "normal"
    MILD_ANOMALY = "mild_anomaly"
    CRITICAL = "critical"
    RANDOM = "random"


SCENARIO_RANGES = {
    ScenarioType.NORMAL: {
        "bpm": (60, 90), "spo2": (96.0, 99.5),
        "systolic": (110, 130), "diastolic": (70, 85),
        "hrv": (35.0, 65.0), "temperature": (36.2, 37.0),
    },
    ScenarioType.MILD_ANOMALY: {
        "bpm": (100, 125), "spo2": (89.0, 93.5),
        "systolic": (140, 165), "diastolic": (92, 105),
        "hrv": (15.0, 25.0), "temperature": (37.8, 38.8),
    },
    ScenarioType.CRITICAL: {
        "bpm": (140, 195), "spo2": (75.0, 88.0),
        "systolic": (175, 220), "diastolic": (105, 130),
        "hrv": (3.0, 12.0), "temperature": (39.0, 40.5),
    },
}


class SimulateResponse(BaseModel):
    scenario: str
    vitals_injected: dict
    ai_condition: Optional[str] = None
    ai_severity: Optional[str] = None
    ai_reasoning: Optional[str] = None
    ai_actions: Optional[list] = None
    risk_score: Optional[int] = None
    risk_level: Optional[str] = None
    message: str


# ── Vital Generator ──────────────────────────────────────────────

def _generate_vitals(scenario: ScenarioType, profile_key: str = "healthy_adult") -> dict:
    """Generate vital signs for a given scenario with circadian adjustment."""
    ranges = SCENARIO_RANGES[scenario]
    circ = _circadian_offset()
    profile = PATIENT_PROFILES.get(profile_key, PATIENT_PROFILES["healthy_adult"])

    if scenario == ScenarioType.NORMAL:
        hr = _noise(profile["hr_base"] + circ["hr"], 3)
        spo2 = _noise(profile["spo2_base"], 0.4)
        temp = _noise(profile["temp_base"] + circ["temp"], 0.15)
        hrv = _noise(profile["hrv_base"], 3)
        sys_bp = int(_noise(profile["sys_base"], 5))
        dia_bp = int(_noise(profile["dia_base"], 4))
    elif scenario == ScenarioType.MILD_ANOMALY:
        hr = _noise(MIMIC_MILD["hr"], 8)
        spo2 = _noise(MIMIC_MILD["spo2"], 1.5)
        temp = _noise(MIMIC_MILD["temp"], 0.4)
        hrv = _noise(MIMIC_MILD["hrv"], 3)
        sys_bp = int(_noise(MIMIC_MILD["sys"], 8))
        dia_bp = int(_noise(MIMIC_MILD["dia"], 5))
    else:  # CRITICAL
        params = random.choice([MIMIC_CRITICAL_SEPSIS, MIMIC_CRITICAL_CARDIAC])
        hr = _noise(params["hr"], 12)
        spo2 = _noise(params["spo2"], 3)
        temp = _noise(params["temp"], 0.5)
        hrv = _noise(params["hrv"], 2)
        sys_bp = int(_noise(params["sys"], 10))
        dia_bp = int(_noise(params["dia"], 8))

    # Physiological correlation: high HR → lower HRV
    hrv_penalty = max(0, (hr - 90) * 0.3)
    hrv = max(2.0, hrv - hrv_penalty)

    # Clamp
    hr = max(25, min(250, hr))
    spo2 = max(60, min(100, spo2))
    temp = max(33, min(43, temp))
    hrv = max(1, min(120, hrv))
    sys_bp = max(50, min(250, sys_bp))
    dia_bp = max(30, min(150, dia_bp))

    return {
        "bpm": int(hr),
        "heart_rate": round(hr, 1),
        "spo2": round(spo2, 1),
        "systolic": sys_bp,
        "diastolic": dia_bp,
        "hrv": round(hrv, 1),
        "temperature": round(temp, 1),
    }


# ── Endpoints ────────────────────────────────────────────────────

@router.post("/scenario", response_model=SimulateResponse)
async def simulate_scenario(
    scenario: ScenarioType = Query(ScenarioType.CRITICAL, description="Scenario type"),
    user_id: str = Query("U002", description="User ID"),
    profile: str = Query("healthy_adult", description="Patient profile"),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate scenario-based vitals and inject through full pipeline:
    Rule Engine → 5-Agent LangGraph → DB → WebSocket → SMS/Email/Call
    """
    if scenario == ScenarioType.RANDOM:
        scenario = random.choice([ScenarioType.NORMAL, ScenarioType.MILD_ANOMALY, ScenarioType.CRITICAL])

    vitals_data = _generate_vitals(scenario, profile)

    vital_input = VitalCreate(
        user_id=user_id,
        heart_rate=vitals_data["heart_rate"],
        bpm=vitals_data["bpm"],
        spo2=vitals_data["spo2"],
        systolic=vitals_data["systolic"],
        diastolic=vitals_data["diastolic"],
        hrv=vitals_data["hrv"],
        temperature=vitals_data["temperature"],
    )

    result = await create_vital(vital_input, db)

    # Parse AI actions
    ai_actions = []
    if result.actions:
        try:
            parsed = json.loads(result.actions)
            ai_actions = parsed if isinstance(parsed, list) else [str(parsed)]
        except (json.JSONDecodeError, TypeError):
            ai_actions = [result.actions] if result.actions else []

    return SimulateResponse(
        scenario=scenario.value,
        vitals_injected=vitals_data,
        ai_condition=result.condition,
        ai_severity=result.severity,
        ai_reasoning=result.reasoning,
        ai_actions=ai_actions,
        risk_score=None,
        risk_level=None,
        message=f"{scenario.value.replace('_', ' ').title()} vitals injected for {user_id}",
    )


@router.post("/inject")
async def inject_vital(vital: VitalCreate, db: AsyncSession = Depends(get_db)):
    """Inject a fully custom vital reading through the pipeline."""
    return await create_vital(vital, db)


from sqlalchemy.future import select

@router.post("/seed")
async def seed_database(db: AsyncSession = Depends(get_db)):
    """Seed database with demo users, doctors, and patient profiles."""
    # Prevent duplicate seeding
    result = await db.execute(select(models.User).where(models.User.id == "U001"))
    if result.scalars().first():
        return {"message": "Database already seeded. Skipping."}

    try:
        from faker import Faker
        fake = Faker()
    except ImportError:
        fake = None

    # Seed doctors
    demo_doctors = [
        ("Dr. Priya Sharma", "Cardiology", "+91-40-23607777", "Apollo Hospitals", 17.4121, 78.4347),
        ("Dr. Ravi Patel", "Neurology", "+91-40-44885000", "KIMS Hospital", 17.4156, 78.4525),
        ("Dr. Ananya Gupta", "Emergency Medicine", "+91-40-45678999", "Yashoda Hospitals", 17.4065, 78.4728),
        ("Dr. Vikram Singh", "General Practice", "+91-40-67001111", "Continental Hospital", 17.4250, 78.3400),
        ("Dr. Meera Nair", "Pulmonology", "+91-40-30418888", "Care Hospitals", 17.3616, 78.4747),
    ]
    for name, spec, phone, hospital, lat, lng in demo_doctors:
        doctor = models.Doctor(
            name=name, specialization=spec, phone=phone,
            hospital=hospital, location_lat=lat, location_lng=lng,
        )
        db.add(doctor)

    # Seed demo users
    demo_users = [
        ("U001", "Aarav Mehta", 28, "Male", "+919260003000", 17.385, 78.487),
        ("U002", "Diya Sharma", 45, "Female", "+919260003001", 17.412, 78.435),
        ("U003", "Kabir Patel", 67, "Male", "+919260003002", 17.362, 78.475),
    ]
    for uid, name, age, gender, phone, lat, lng in demo_users:
        user = models.User(
            id=uid, name=name, age=age, gender=gender, phone=phone,
            location_lat=lat, location_lng=lng,
            emergency_contacts=json.dumps([{"name": "Family", "phone": "+919260003000"}]),
            medical_history=json.dumps({"allergies": [], "chronic_conditions": []}),
        )
        db.add(user)

        # Create patient profiles
        profile = models.PatientProfile(user_id=uid)
        db.add(profile)

    await db.commit()
    return {"message": "Database seeded with 3 demo users, 5 doctors, and patient profiles"}


@router.get("/test-twilio")
async def test_twilio():
    """Diagnostic: test SMS + Call directly."""
    from .services.emergency import emergency_service
    results = {
        "twilio_enabled": __import__("os").environ.get("TWILIO_ENABLED", "true"),
        "client_initialized": emergency_service.client is not None,
        "from_number": emergency_service.from_number,
    }
    return results


@router.get("/profiles")
async def get_profiles():
    """Return available patient profiles."""
    return {k: {"label": v["label"]} for k, v in PATIENT_PROFILES.items()}
