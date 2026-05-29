from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
from ..db.database import get_db
from ..db import models
from .. import schemas

router = APIRouter()

@router.post("/", response_model=schemas.UserResponse)
async def create_user(user: schemas.UserCreate, db: AsyncSession = Depends(get_db)):
    # 1. Create User
    db_user = models.User(**user.model_dump())
    db.add(db_user)
    
    # 2. Create corresponding PatientProfile baseline shell
    db_profile = models.PatientProfile(
        user_id=user.id,
        conditions=user.medical_history
    )
    db.add(db_profile)
    
    await db.commit()
    await db.refresh(db_user)
    return db_user

@router.get("/", response_model=List[schemas.UserResponse])
async def read_users(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.User).offset(skip).limit(limit))
    users = result.scalars().all()
    return list(users)

@router.get("/{user_id}", response_model=schemas.UserResponse)
async def read_user(user_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user
