from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
from ..db.database import get_db
from ..db import models
from .. import schemas

router = APIRouter()

@router.post("/", response_model=schemas.DoctorResponse)
async def create_doctor(doctor: schemas.DoctorCreate, db: AsyncSession = Depends(get_db)):
    db_doctor = models.Doctor(**doctor.model_dump())
    db.add(db_doctor)
    await db.commit()
    await db.refresh(db_doctor)
    return db_doctor

@router.get("/", response_model=List[schemas.DoctorResponse])
async def read_doctors(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.Doctor).offset(skip).limit(limit))
    doctors = result.scalars().all()
    return list(doctors)
