from typing import List, Optional, Any
from pydantic import BaseModel, ConfigDict
from datetime import datetime

class VitalBase(BaseModel):
    user_id: str
    bpm: Optional[int] = None
    spo2: Optional[float] = None
    systolic: Optional[int] = None
    diastolic: Optional[int] = None
    hrv: Optional[float] = None
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

class UserBase(BaseModel):
    id: str
    name: str
    age: int
    gender: str
    phone: str
    location_lat: float
    location_lng: float
    emergency_contacts: str

class UserCreate(UserBase):
    pass

class UserResponse(UserBase):
    onboarded_at: datetime
    model_config = ConfigDict(from_attributes=True)

class AlertResponse(BaseModel):
    id: int
    user_id: str
    timestamp: datetime
    condition: str
    vitals_snapshot: str
    escalated: int
    resolved: int
    model_config = ConfigDict(from_attributes=True)

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
