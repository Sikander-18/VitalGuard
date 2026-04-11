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
    return state

def handle_future(state: AgentState) -> AgentState:
    print(f"[{state['user_id']}] Handled Future Alert: {state['reasoning']}")
    return state

def handle_critical(state: AgentState) -> AgentState:
    print(f"[{state['user_id']}] !!! CRITICAL NODE TRIGGERED !!!")
    
    # Real Emergency Contacts from Onboarding
    user_contacts_raw = state.get("emergency_contacts", "[]")
    try:
        # DB stores it as JSON string like '[{"name":"X", "phone":"Y"}]'
        contacts = json.loads(user_contacts_raw)
    except:
        contacts = []

    if contacts and len(contacts) > 0:
        print(f"[{state['user_id']}] Found {len(contacts)} user contacts. Initiating calls...")
        message = f"Emergency Alert! Vital Guard has detected a critical health condition for {state.get('user_id')}. Reasoning: {state['reasoning']}. Please check the dashboard immediately."
        
        for contact in contacts:
            phone = contact.get("phone")
            name = contact.get("name", "Emergency Contact")
            if phone:
                print(f"[{state['user_id']}] Calling {name} at {phone}...")
                emergency_service.trigger_call(phone, message)
    else:
        # Fallback to default if no user contacts found
        target = settings.TWILIO_TARGET_PHONE_NUMBER
        print(f"[{state['user_id']}] No user contacts. Fallback to settings: '{target}'")
        
        if target:
            message = f"Alert! Pulse Guard has detected a critical condition for patient {state['user_id']}. Reasoning: {state['reasoning']}."
            emergency_service.trigger_call(target, message)
        else:
            print(f"[{state['user_id']}] SKIP CALL: No phone numbers available anywhere!")
        
    return state
