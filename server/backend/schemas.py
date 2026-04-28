"""
VitalGuard v2 — Pydantic Schemas
Request/response models for all API endpoints.
"""

from typing import List, Optional
from pydantic import BaseModel, ConfigDict
from datetime import datetime


# ── Vitals ────────────────────────────────────────────────────────

class VitalBase(BaseModel):
    user_id: str
    heart_rate: Optional[float] = None
    spo2: Optional[float] = None
    temperature: Optional[float] = None
    hrv: Optional[float] = None
    systolic: Optional[int] = None
    diastolic: Optional[int] = None
    source: Optional[str] = "simulator"
    # Legacy fields
    bpm: Optional[int] = None
    condition: Optional[str] = "normal"
    severity: Optional[str] = "low"
    reasoning: Optional[str] = None
    actions: Optional[str] = None
    raw_json: Optional[str] = None


class VitalCreate(VitalBase):
    pass


class VitalResponse(VitalBase):
    id: int
    timestamp: datetime
    model_config = ConfigDict(from_attributes=True)


# ── Users ─────────────────────────────────────────────────────────

class UserBase(BaseModel):
    id: str
    name: str
    age: int
    gender: str
    phone: str
    location_lat: float
    location_lng: float
    emergency_contacts: str
    medical_history: Optional[str] = "{}"


class UserCreate(UserBase):
    pass


class UserResponse(UserBase):
    onboarded_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ── Alerts ────────────────────────────────────────────────────────

class AlertBase(BaseModel):
    user_id: str
    risk_level: Optional[str] = "LOW"
    risk_score: Optional[int] = 0
    mews_score: Optional[int] = 0
    contributing_factors: Optional[str] = "[]"
    ai_summary: Optional[str] = ""
    decided_action: Optional[str] = "log"
    action_result: Optional[str] = "{}"


class AlertResponse(BaseModel):
    id: int
    user_id: str
    timestamp: datetime
    risk_level: Optional[str] = "LOW"
    risk_score: Optional[int] = 0
    mews_score: Optional[int] = 0
    contributing_factors: Optional[str] = "[]"
    ai_summary: Optional[str] = ""
    decided_action: Optional[str] = "log"
    action_result: Optional[str] = "{}"
    escalated: Optional[bool] = False
    resolved: Optional[bool] = False
    resolved_at: Optional[datetime] = None
    # Legacy
    condition: Optional[str] = None
    vitals_snapshot: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


# ── Doctors ───────────────────────────────────────────────────────

class DoctorBase(BaseModel):
    name: str
    specialization: str
    phone: str
    hospital: str
    location_lat: float
    location_lng: float


class DoctorCreate(DoctorBase):
    pass


class DoctorResponse(DoctorBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


# ── Patient Profiles ─────────────────────────────────────────────

class PatientProfileBase(BaseModel):
    user_id: str
    baseline_hr: Optional[float] = 72.0
    baseline_spo2: Optional[float] = 98.0
    baseline_temp: Optional[float] = 36.6
    baseline_hrv: Optional[float] = 45.0
    conditions: Optional[str] = "[]"
    medications: Optional[str] = "[]"


class PatientProfileResponse(PatientProfileBase):
    id: int
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ── Agent Logs ────────────────────────────────────────────────────

class AgentLogResponse(BaseModel):
    id: int
    user_id: str
    timestamp: datetime
    vitals_snapshot: Optional[str] = "{}"
    risk_input: Optional[str] = "{}"
    agent_output: Optional[str] = "{}"
    trace: Optional[str] = "[]"
    duration_ms: Optional[int] = 0
    model_config = ConfigDict(from_attributes=True)


# ── Risk Assessment (used internally, not a DB model) ────────────

class RiskAssessmentSchema(BaseModel):
    score: int = 0
    level: str = "LOW"
    mews_score: int = 0
    contributing_factors: List[str] = []
    summary: str = ""
    trend_alert: Optional[str] = None
    trend_summary: Optional[dict] = None
    validated_by: str = "deterministic"
