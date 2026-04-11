import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey
from .database import Base

class Vital(Base):
    __tablename__ = "vitals"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(String, index=True, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    bpm = Column(Integer)
    spo2 = Column(Float)
    systolic = Column(Integer)
    diastolic = Column(Integer)
    hrv = Column(Float)
    condition = Column(String) # 'normal' | 'future_alert' | 'critical'
    severity = Column(String) # 'low' | 'medium' | 'high'
    reasoning = Column(Text)
    actions = Column(Text) # JSON string of recommended actions/remedies
    raw_json = Column(Text) # full BLE payload for future analysis

class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, index=True)
    name = Column(String)
    age = Column(Integer)
    gender = Column(String)
    phone = Column(String)
    location_lat = Column(Float)
    location_lng = Column(Float)
    emergency_contacts = Column(Text) # JSON array [{name, phone}]
    onboarded_at = Column(DateTime, default=datetime.datetime.utcnow)

class Alert(Base):
    __tablename__ = "alerts"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(String, index=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    condition = Column(String)
    vitals_snapshot = Column(Text) # JSON
    escalated = Column(Integer, default=0)
    resolved = Column(Integer, default=0)

class Doctor(Base):
    __tablename__ = "doctors"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String)
    specialization = Column(String)
    phone = Column(String)
    hospital = Column(String)
    location_lat = Column(Float)
    location_lng = Column(Float)
