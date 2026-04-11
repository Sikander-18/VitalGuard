import random
import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from faker import Faker

from .db.database import get_db, engine, Base
from .db import models
from .schemas import VitalCreate

# Re-use our vitals router logic to hit the websocket broadcast
from .routes.vitals import create_vital

router = APIRouter()
fake = Faker()

@router.post("/inject")
async def inject_vital(vital: VitalCreate, db: AsyncSession = Depends(get_db)):
    """
    Simulate frontend sending in a customized fake reading.
    """
    # Just routes through the normal create_vital function to leverage rule engine/websocket
    return await create_vital(vital, db)

@router.post("/seed")
async def seed_database(db: AsyncSession = Depends(get_db)):
    """
    Seed User and Doctor tables with Fake data for Demo
    """
    # 5 Fake Doctors
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
        
    # 5 Fake Users
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
