from typing import TypedDict, Dict, Any, Optional
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
import json

from ..config import settings
from ..services.emergency import emergency_service

class AnalysisOutput(BaseModel):
    condition: str = Field(description="One of 'normal', 'future_alert', 'critical'")
    severity: str = Field(description="One of 'low', 'medium', 'high'")
    reasoning: str = Field(description="Short explanation of the classification")
    actions: list[str] = Field(description="List of 3-5 recommended immediate actions or remedies for the patient to take based on the condition")

# Initialize LLM
llm = None
if settings.GROQ_API_KEY:
    llm = ChatGroq(
        api_key=settings.GROQ_API_KEY,
        model_name="llama-3.3-70b-versatile",
        temperature=0
    ).with_structured_output(AnalysisOutput)

class AgentState(TypedDict):
    vitals: Dict[str, Any]
    user_id: str
    emergency_contacts: Optional[str]
    condition: Optional[str]
    severity: Optional[str]
    reasoning: Optional[str]
    actions: Optional[list[str]]

def analyze_vitals(state: AgentState) -> AgentState:
    vitals = state.get("vitals", {})
    
    if not llm:
        # Fallback to simple rule based logic if no API key
        bpm = vitals.get("bpm", 70)
        spo2 = vitals.get("spo2", 98)
        if bpm > 150 or spo2 < 90:
            state["condition"] = "critical"
            state["severity"] = "high"
            state["reasoning"] = "Rule-based: Critical thresholds exceeded."
            state["actions"] = ["Sit upright immediately to improve breathing", "Call emergency services if alone", "Do NOT exert yourself physically"]
        else:
            state["condition"] = "normal"
            state["severity"] = "low"
            state["reasoning"] = "Rule-based: Within normal bounds."
            state["actions"] = ["Continue routine monitoring"]
        return state

    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a medical AI monitoring patient vitals in real-time. Analyze the vitals and determine the condition: 'normal', 'future_alert', or 'critical'."),
        ("user", "Patient Vitals: {vitals}\nAnalyze and categorize.")
    ])
    
    chain = prompt | llm
    try:
        result = chain.invoke({"vitals": json.dumps(vitals)})
        state["condition"] = result.condition
        state["severity"] = result.severity
        state["reasoning"] = result.reasoning
        state["actions"] = result.actions
    except Exception as e:
        print(f"AI Analysis Error: {str(e)}")
        state["condition"] = "normal"
        state["severity"] = "low"
        state["reasoning"] = "AI Analysis Error: Falling back to normal. Detailed analysis unavailable."
        state["actions"] = []
        
    return state

def handle_normal(state: AgentState) -> AgentState:
    print(f"[{state['user_id']}] Handled Normal: {state['reasoning']}")
    from ..services.emergency import update_incident_state
    update_incident_state("normal")
    return state

def handle_future(state: AgentState) -> AgentState:
    print(f"[{state['user_id']}] Handled Future Alert: {state['reasoning']}")
    
    from ..services.emergency import emergency_service, try_fire, update_incident_state
    update_incident_state("future_alert")
    
    # One-shot SMS to patient
    if try_fire("sms_patient"):
        vitals = state.get("vitals", {})
        sms_body = (
            f"⚠️ VitalGuard Health Alert\n"
            f"Patient: {settings.PATIENT_NAME}\n"
            f"HR: {vitals.get('bpm', '--')} bpm | SpO2: {vitals.get('spo2', '--')}%\n"
            f"BP: {vitals.get('systolic', '--')}/{vitals.get('diastolic', '--')} mmHg\n"
            f"Concern: {state.get('reasoning', 'Vitals trending abnormal')}\n"
            f"Please check your vitals. Contact a doctor if you feel unwell."
        )
        target = settings.PATIENT_PHONE or settings.TWILIO_TARGET_PHONE_NUMBER
        if target:
            emergency_service.trigger_sms(target, sms_body)
    else:
        print(f"[{state['user_id']}] Patient SMS already sent this incident — skipped")
    
    return state

def handle_critical(state: AgentState) -> AgentState:
    print(f"[{state['user_id']}] !!! CRITICAL NODE TRIGGERED !!!")
    
    from ..services.emergency import emergency_service, try_fire, update_incident_state, unfire
    update_incident_state("critical")
    
    vitals = state.get("vitals", {})
    reasoning = state.get("reasoning", "Critical vitals detected")
    
    # Resolve emergency contacts: onboarding contacts + config fallback (deduped)
    user_contacts_raw = state.get("emergency_contacts", "[]")
    try:
        contacts = json.loads(user_contacts_raw)
    except:
        contacts = []
    
    # Build target phone list — collect all available numbers, dedup by phone
    seen_phones = set()
    target_phones = []
    
    # 1. Onboarding contacts first
    if contacts:
        for c in contacts:
            phone = c.get("phone")
            if phone and phone not in seen_phones:
                target_phones.append({"name": c.get("name", "Contact"), "phone": phone})
                seen_phones.add(phone)
    
    # 2. Always add config fallback (verified number) if not already in list
    config_phone = settings.EMERGENCY_CONTACT_PHONE or settings.TWILIO_TARGET_PHONE_NUMBER
    if config_phone and config_phone not in seen_phones:
        target_phones.append({"name": settings.EMERGENCY_CONTACT_NAME, "phone": config_phone})
        seen_phones.add(config_phone)
    
    # ── 1. ONE-SHOT SMS to emergency contacts ────────────────────
    if try_fire("sms_emergency"):
        sms_body = (
            f"🚨 EMERGENCY — VitalGuard Alert\n"
            f"Patient: {settings.PATIENT_NAME}\n"
            f"HR: {vitals.get('bpm', '--')} bpm | SpO2: {vitals.get('spo2', '--')}%\n"
            f"BP: {vitals.get('systolic', '--')}/{vitals.get('diastolic', '--')} mmHg\n"
            f"HRV: {vitals.get('hrv', '--')} ms\n"
            f"Reason: {reasoning}\n"
            f"Emergency services have been alerted. Please respond immediately."
        )
        any_sms_success = False
        for contact in target_phones:
            print(f"[{state['user_id']}] SMS → {contact['name']} at {contact['phone']}")
            result = emergency_service.trigger_sms(contact["phone"], sms_body)
            if result.get("mode") == "live":
                any_sms_success = True
        # If ALL SMS failed, unfire so next attempt can retry
        if not any_sms_success:
            unfire("sms_emergency")
            print(f"[{state['user_id']}] All SMS failed — lock reset for retry")
    else:
        print(f"[{state['user_id']}] Emergency SMS already sent this incident — skipped")
    
    # ── 2. ONE-SHOT VOICE CALL to emergency contacts ─────────────
    if try_fire("voice_emergency"):
        voice_message = (
            f"Emergency alert from Vital Guard. "
            f"{settings.PATIENT_NAME} is experiencing a critical health event. "
            f"Heart rate is {vitals.get('bpm', 'unknown')} beats per minute. "
            f"Oxygen level is {vitals.get('spo2', 'unknown')} percent. "
            f"Please respond immediately."
        )
        any_call_success = False
        for contact in target_phones:
            print(f"[{state['user_id']}] CALL → {contact['name']} at {contact['phone']}")
            result = emergency_service.trigger_call(contact["phone"], voice_message)
            if result.get("mode") == "live":
                any_call_success = True
        if not any_call_success:
            unfire("voice_emergency")
            print(f"[{state['user_id']}] All calls failed — lock reset for retry")
    else:
        print(f"[{state['user_id']}] Emergency voice call already placed this incident — skipped")
    
    # ── 3. ONE-SHOT EMAIL to doctor ──────────────────────────────
    if try_fire("email_doctor"):
        subject = f"[VitalGuard] 🚨 CRITICAL — {settings.PATIENT_NAME}"
        body = (
            f"Dear Doctor,\n\n"
            f"VitalGuard has detected a CRITICAL health condition for patient {settings.PATIENT_NAME}.\n\n"
            f"Patient Vitals at time of alert:\n"
            f"  Heart Rate:       {vitals.get('bpm', '--')} bpm\n"
            f"  SpO2:             {vitals.get('spo2', '--')}%\n"
            f"  Blood Pressure:   {vitals.get('systolic', '--')}/{vitals.get('diastolic', '--')} mmHg\n"
            f"  HRV:              {vitals.get('hrv', '--')} ms\n\n"
            f"AI Reasoning: {reasoning}\n\n"
            f"Emergency contacts have been notified.\n"
            f"Please take immediate action.\n\n"
            f"— VitalGuard System"
        )
        emergency_service.send_doctor_email(subject, body)
    else:
        print(f"[{state['user_id']}] Doctor email already sent this incident — skipped")
    
    return state

