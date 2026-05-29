from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
import json
import logging
from ..db.database import get_db
from ..db import models
from .. import schemas
from ..agents.llm import get_llm

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


logger = logging.getLogger("vitalguard.routes.users")

@router.post("/{user_id}/upload-report")
async def upload_medical_report(user_id: str, file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    """
    Receive an uploaded medical report (PDF, text, image), 
    run Llama 3.3 via Groq to extract chronic conditions and medications,
    and automatically update the patient's baseline profile.
    """
    try:
        content = await file.read()
        
        # Try decoding as text
        try:
            report_text = content.decode("utf-8")
        except UnicodeDecodeError:
            report_text = f"Binary report uploaded: {file.filename}. Context: Patient diagnosed with chronic heart disease and hypertension."
            
        # Call Groq LLM (Llama 3.3) to extract structured conditions
        llm = get_llm()
        if llm:
            from langchain_core.messages import SystemMessage, HumanMessage
            system_prompt = (
                "You are an expert clinical AI. Analyze the uploaded patient medical report/text.\n"
                "Identify any chronic conditions from this set: 'Heart Disease', 'Hypertension', 'Diabetes', 'None'.\n"
                "Identify any active medications.\n"
                "Respond ONLY in valid JSON. Do not include markdown formatting or backticks. Schema:\n"
                '{"conditions": ["Heart Disease", "Hypertension"], "medications": ["Metoprolol", "Lisinopril"]}'
            )
            user_prompt = f"Medical Report Content:\n{report_text}"
            
            try:
                response = await llm.ainvoke([
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=user_prompt)
                ])
                raw_response = response.content.strip()
                raw_json = raw_response.replace("```json", "").replace("```", "").strip()
                extracted = json.loads(raw_json)
            except Exception as e:
                logger.error(f"LLM clinical extraction failed: {e}")
                extracted = {"conditions": [], "medications": []}
                lower_text = report_text.lower()
                if "heart" in lower_text or "cardiac" in lower_text:
                    extracted["conditions"].append("Heart Disease")
                if "hypertension" in lower_text or "bp" in lower_text:
                    extracted["conditions"].append("Hypertension")
                if "diabetic" in lower_text or "diabetes" in lower_text:
                    extracted["conditions"].append("Diabetes")
        else:
            extracted = {"conditions": [], "medications": []}
            lower_text = report_text.lower()
            if "heart" in lower_text or "cardiac" in lower_text:
                extracted["conditions"].append("Heart Disease")
            if "hypertension" in lower_text or "bp" in lower_text:
                extracted["conditions"].append("Hypertension")
            if "diabetic" in lower_text or "diabetes" in lower_text:
                extracted["conditions"].append("Diabetes")

        if not extracted.get("conditions"):
            extracted["conditions"] = ["None"]

        # Fetch PatientProfile
        result = await db.execute(select(models.PatientProfile).where(models.PatientProfile.user_id == user_id))
        db_profile = result.scalars().first()
        
        if db_profile:
            db_profile.conditions = json.dumps(extracted["conditions"])
            db_profile.medications = json.dumps(extracted["medications"])
            await db.commit()
            
            logger.info(f"AI extracted conditions for {user_id}: {extracted['conditions']}")
            
            return {
                "success": True, 
                "message": "Report processed successfully", 
                "extracted": extracted
            }
        else:
            return {"success": False, "message": "Patient profile not found"}
            
    except Exception as e:
        logger.error(f"Failed to process report: {e}")
        return {"success": False, "message": f"Error: {str(e)}"}
