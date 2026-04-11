"""
VitalGuard — Simulation Router
Generates and injects realistic vital sign data for demo purposes.
Scenario-based vitals route through the full pipeline:
  Rule Engine → AI Agent (Groq) → DB → WebSocket broadcast → SMS/Email/Call
"""
import random
import json
from enum import Enum
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from faker import Faker
from pydantic import BaseModel

from .db.database import get_db
from .db import models
from .schemas import VitalCreate
from .routes.vitals import create_vital

router = APIRouter()
fake = Faker()


# ── Scenario Definitions ─────────────────────────────────────────

class ScenarioType(str, Enum):
    NORMAL = "normal"
    MILD_ANOMALY = "mild_anomaly"
    CRITICAL = "critical"
    RANDOM = "random"


SCENARIO_RANGES = {
    ScenarioType.NORMAL: {
        "bpm":       (60, 90),
        "spo2":      (96.0, 99.5),
        "systolic":  (110, 130),
        "diastolic": (70, 85),
        "hrv":       (35.0, 65.0),
    },
    ScenarioType.MILD_ANOMALY: {
        "bpm":       (100, 125),
        "spo2":      (89.0, 93.5),
        "systolic":  (140, 165),
        "diastolic": (92, 105),
        "hrv":       (15.0, 25.0),
    },
    ScenarioType.CRITICAL: {
        "bpm":       (140, 195),
        "spo2":      (75.0, 88.0),
        "systolic":  (175, 220),
        "diastolic": (105, 130),
        "hrv":       (3.0, 12.0),
    },
}


class SimulateResponse(BaseModel):
    scenario: str
    vitals_injected: dict
    ai_condition: Optional[str] = None
    ai_severity: Optional[str] = None
    ai_reasoning: Optional[str] = None
    ai_actions: Optional[list] = None
    message: str


def _generate_vitals(scenario: ScenarioType) -> dict:
    """Generate a single set of vital signs for the given scenario."""
    ranges = SCENARIO_RANGES[scenario]
    return {
        "bpm":       random.randint(*ranges["bpm"]),
        "spo2":      round(random.uniform(*ranges["spo2"]), 1),
        "systolic":  random.randint(*ranges["systolic"]),
        "diastolic": random.randint(*ranges["diastolic"]),
        "hrv":       round(random.uniform(*ranges["hrv"]), 1),
    }


# ── Endpoints ────────────────────────────────────────────────────

@router.post("/scenario", response_model=SimulateResponse)
async def simulate_scenario(
    scenario: ScenarioType = Query(ScenarioType.CRITICAL, description="Scenario type to simulate"),
    user_id: str = Query("U002", description="User ID to inject vitals for"),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate scenario-based vital signs and inject them through the full pipeline:
    Rule Engine → AI Agent (Groq) → DB → WebSocket → SMS/Email/Call
    """
    if scenario == ScenarioType.RANDOM:
        scenario = random.choice([ScenarioType.NORMAL, ScenarioType.MILD_ANOMALY, ScenarioType.CRITICAL])

    vitals_data = _generate_vitals(scenario)

    vital_input = VitalCreate(
        user_id=user_id,
        bpm=vitals_data["bpm"],
        spo2=vitals_data["spo2"],
        systolic=vitals_data["systolic"],
        diastolic=vitals_data["diastolic"],
        hrv=vitals_data["hrv"],
    )

    # Run through the full pipeline
    result = await create_vital(vital_input, db)

    # Safely parse AI actions
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
        message=f"✅ {scenario.value.replace('_', ' ').title()} vitals injected for {user_id} → pipeline complete.",
    )


@router.post("/inject")
async def inject_vital(vital: VitalCreate, db: AsyncSession = Depends(get_db)):
    """Inject a fully custom vital reading through the pipeline."""
    return await create_vital(vital, db)


@router.post("/seed")
async def seed_database(db: AsyncSession = Depends(get_db)):
    """Seed User and Doctor tables with fake data for demo."""
    for _ in range(5):
        doctor = models.Doctor(
            name=fake.name(),
            specialization=random.choice(["Cardiology", "Neurology", "General Practice"]),
            phone=fake.phone_number(),
            hospital=fake.company() + " Hospital",
            location_lat=float(fake.latitude()),
            location_lng=float(fake.longitude())
        )
        db.add(doctor)

    for _ in range(5):
        user = models.User(
            id=fake.uuid4(),
            name=fake.name(),
            age=random.randint(20, 80),
            gender=random.choice(["Male", "Female"]),
            phone=fake.phone_number(),
            location_lat=float(fake.latitude()),
            location_lng=float(fake.longitude()),
            emergency_contacts='[{"name": "Emergency Contact", "phone": "123-456-7890"}]'
        )
        db.add(user)

    await db.commit()
    return {"message": "Database seeded with users and doctors"}


@router.get("/test-twilio")
async def test_twilio():
    """
    Diagnostic: test SMS + Call directly and return exact results/errors.
    """
    from .services.emergency import emergency_service
    from .config import settings

    results = {
        "twilio_enabled": settings.TWILIO_ENABLED,
        "client_initialized": emergency_service.client is not None,
        "from_number": settings.TWILIO_PHONE_NUMBER,
        "target_number": settings.EMERGENCY_CONTACT_PHONE or settings.TWILIO_TARGET_PHONE_NUMBER,
        "sms_result": None,
        "call_result": None,
    }

    target = results["target_number"]
    if not target:
        results["error"] = "No target phone number configured"
        return results

    # Test SMS
    results["sms_result"] = emergency_service.trigger_sms(target, "VitalGuard Test: SMS is working!")

    # Test Call
    results["call_result"] = emergency_service.trigger_call(target, "This is a test from Vital Guard. SMS and call integration is working correctly.")

    return results
