"""
VitalGuard v2 — Database Models
5 tables: users, vitals, alerts, patient_profiles, agent_logs
Designed for easy migration to PostgreSQL.
"""

import datetime
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Text, Boolean, ForeignKey
)
from .database import Base


class User(Base):
    """Patient accounts — created during onboarding."""
    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    age = Column(Integer)
    gender = Column(String)
    phone = Column(String)
    location_lat = Column(Float)
    location_lng = Column(Float)
    emergency_contacts = Column(Text, default="[]")        # JSON array [{name, phone}]
    medical_history = Column(Text, default="{}")            # JSON object
    onboarded_at = Column(DateTime, default=datetime.datetime.utcnow)


class Vital(Base):
    """Every vital sign reading — the core time-series data."""
    __tablename__ = "vitals"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(String, index=True, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    heart_rate = Column(Float)
    spo2 = Column(Float)
    temperature = Column(Float)
    hrv = Column(Float)
    systolic = Column(Integer)
    diastolic = Column(Integer)
    source = Column(String, default="simulator")            # simulator | ble | manual
    # Legacy fields kept for backward compatibility
    bpm = Column(Integer)
    condition = Column(String, default="normal")            # normal | future_alert | critical
    severity = Column(String, default="low")                # low | medium | high
    reasoning = Column(Text)
    actions = Column(Text)                                  # JSON string
    raw_json = Column(Text)


class Alert(Base):
    """Generated alerts when risk thresholds are crossed."""
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(String, index=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    risk_level = Column(String, default="LOW")              # LOW | MODERATE | HIGH | CRITICAL
    risk_score = Column(Integer, default=0)
    mews_score = Column(Integer, default=0)
    contributing_factors = Column(Text, default="[]")       # JSON array
    ai_summary = Column(Text, default="")
    decided_action = Column(String, default="log")
    action_result = Column(Text, default="{}")              # JSON
    escalated = Column(Boolean, default=False)
    resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime, nullable=True)
    # Legacy fields
    condition = Column(String)
    vitals_snapshot = Column(Text)


class PatientProfile(Base):
    """Per-patient baseline vitals and medical context."""
    __tablename__ = "patient_profiles"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(String, unique=True, index=True)
    baseline_hr = Column(Float, default=72.0)
    baseline_spo2 = Column(Float, default=98.0)
    baseline_temp = Column(Float, default=36.6)
    baseline_hrv = Column(Float, default=45.0)
    conditions = Column(Text, default="[]")                 # JSON array of conditions
    medications = Column(Text, default="[]")                # JSON array
    updated_at = Column(DateTime, default=datetime.datetime.utcnow)


class AgentLog(Base):
    """Every agent pipeline execution — for explainability and auditing."""
    __tablename__ = "agent_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(String, index=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    vitals_snapshot = Column(Text, default="{}")            # JSON
    risk_input = Column(Text, default="{}")                 # JSON (rule engine output)
    agent_output = Column(Text, default="{}")               # JSON (full pipeline result)
    trace = Column(Text, default="[]")                      # JSON (explainability)
    duration_ms = Column(Integer, default=0)


class Doctor(Base):
    """Doctor/hospital directory for location-based matching."""
    __tablename__ = "doctors"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String)
    specialization = Column(String)
    phone = Column(String)
    hospital = Column(String)
    location_lat = Column(Float)
    location_lng = Column(Float)
