"""
VitalGuard v2 — 5-Agent LangGraph Pipeline Nodes
Each agent reasons using trends, patient history, and baseline deviation.
No hardcoded thresholds inside agents — all reasoning is contextual.

Agents:
  1. Vitals Agent     — Clean + interpret vitals, detect subtle anomalies
  2. Prediction Agent — Forecast short-term future (5-15 min)
  3. Risk Agent       — Classify severity using trends + context
  4. Action Agent     — Decide: ignore / notify / escalate / call
  5. Communication Agent — Generate patient + doctor messages
"""

import json
import logging
import time
from typing import TypedDict, Dict, Any, Optional, List

from .llm import get_llm
from ..services.emergency import emergency_service, try_fire, update_incident_state, unfire
from ..services.location import get_alert_safe_coordinates
from ..config import settings

logger = logging.getLogger("vitalguard.agents")


# ── Shared Memory (Agent State) ──────────────────────────────────

class AgentState(TypedDict):
    # Input
    vitals: Dict[str, Any]
    risk_assessment: Dict[str, Any]
    patient_history: Dict[str, Any]
    location: Dict[str, Any]
    user_id: str
    emergency_contacts: Optional[str]

    # Agent outputs (accumulated)
    vitals_interpretation: str
    prediction: Dict[str, Any]
    risk_classification: Dict[str, Any]
    decided_action: str
    action_reasoning: str
    patient_message: str
    doctor_message: str

    # Metadata
    explainability_trace: List[Dict[str, Any]]
    action_result: Dict[str, Any]
    full_log: Dict[str, Any]

    # Legacy compat
    condition: Optional[str]
    severity: Optional[str]
    reasoning: Optional[str]
    actions: Optional[List[str]]


# ── Helper: safe LLM call ────────────────────────────────────────

async def _llm_call(system_prompt: str, user_prompt: str, fallback: str) -> str:
    """Call LLM with fallback on failure."""
    llm = get_llm()
    if not llm:
        return fallback
    try:
        from langchain_core.messages import SystemMessage, HumanMessage
        response = await llm.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ])
        return response.content.strip()
    except Exception as e:
        logger.warning(f"LLM call failed: {e}")
        return fallback


async def _llm_json_call(system_prompt: str, user_prompt: str, fallback: dict) -> dict:
    """Call LLM expecting JSON response, with fallback."""
    raw = await _llm_call(
        system_prompt + " Respond ONLY in valid JSON, no markdown fences.",
        user_prompt,
        json.dumps(fallback),
    )
    try:
        # Extract JSON from response
        text = raw.replace("```json", "").replace("```", "").strip()
        start = text.find("{")
        end = text.rfind("}") + 1
        if start == -1 or end == 0:
            return fallback
        return json.loads(text[start:end])
    except (json.JSONDecodeError, ValueError):
        return fallback


# ── NODE 1: Vitals Agent ──────────────────────────────────────────

async def vitals_agent(state: AgentState) -> dict:
    """
    Clean + interpret vitals. Detect subtle anomalies by comparing
    against patient baseline, not hardcoded thresholds.
    """
    vitals = state["vitals"]
    risk = state["risk_assessment"]
    history = state.get("patient_history", {})
    trace = list(state.get("explainability_trace", []))

    # Build context
    baseline_info = ""
    if history:
        baseline_info = (
            f"\nPatient Baseline: HR={history.get('baseline_hr', '?')} bpm, "
            f"SpO2={history.get('baseline_spo2', '?')}%, "
            f"Temp={history.get('baseline_temp', '?')}°C, "
            f"HRV={history.get('baseline_hrv', '?')} ms"
        )
        if history.get("conditions"):
            baseline_info += f"\nKnown conditions: {history.get('conditions')}"
        if history.get("medications"):
            baseline_info += f"\nMedications: {history.get('medications')}"

    trend_info = ""
    trend = risk.get("trend_summary") or {}
    if trend:
        trend_info = (
            f"\nTrend (last {trend.get('sample_count', '?')} readings): "
            f"HR slope={trend.get('hr_slope', 0):+.2f}, "
            f"SpO2 slope={trend.get('spo2_slope', 0):+.4f}, "
            f"Temp slope={trend.get('temp_slope', 0):+.4f}"
        )
    if risk.get("trend_alert"):
        trend_info += f"\nPREDICTIVE ALERT: {risk['trend_alert']}"

    hr = vitals.get("heart_rate") or vitals.get("bpm", 0)
    spo2 = vitals.get("spo2", 0)
    temp = vitals.get("temperature", 36.6)
    hrv = vitals.get("hrv", 40)
    systolic = vitals.get("systolic", 120)
    diastolic = vitals.get("diastolic", 80)

    prompt = (
        f"Patient vitals:\n"
        f"  HR={hr} bpm, SpO2={spo2}%, Temp={temp}°C, HRV={hrv} ms\n"
        f"  BP={systolic}/{diastolic} mmHg\n"
        f"  MEWS={risk.get('mews_score', '?')}/14, Rule Score={risk.get('score', '?')}/100\n"
        f"  Flags: {', '.join(risk.get('contributing_factors', [])) or 'None'}"
        f"{baseline_info}{trend_info}\n\n"
        "Provide a concise clinical interpretation (2-3 sentences). "
        "Focus on deviation from baseline, not just absolute values. "
        "Note any subtle anomalies the rule engine might miss."
    )

    # Deterministic fallback
    fallback = (
        f"HR={hr:.0f}bpm, SpO2={spo2:.1f}%, Temp={temp:.1f}°C, HRV={hrv:.1f}ms, "
        f"BP={systolic}/{diastolic}. MEWS={risk.get('mews_score', '?')}/14. "
        f"Risk score {risk.get('score', 0)}/100 ({risk.get('level', 'LOW')})."
    )

    interpretation = await _llm_call(
        "You are a clinical monitoring AI. Be concise, precise, and clinically accurate.",
        prompt,
        f"[Deterministic] {fallback}",
    )

    trace.append({
        "step": "vitals_agent",
        "input_summary": f"HR={hr}, SpO2={spo2}%, T={temp}°C, BP={systolic}/{diastolic}",
        "output": interpretation[:250],
    })

    return {"vitals_interpretation": interpretation, "explainability_trace": trace}


# ── NODE 2: Prediction Agent ─────────────────────────────────────

async def prediction_agent(state: AgentState) -> dict:
    """
    Forecast short-term future (5-15 min) using trends + patient context.
    Learn patient baseline by comparing current vs. stored profile.
    """
    vitals = state["vitals"]
    risk = state["risk_assessment"]
    interpretation = state.get("vitals_interpretation", "")
    history = state.get("patient_history", {})
    trace = list(state.get("explainability_trace", []))

    trend = risk.get("trend_summary") or {}
    trend_alert = risk.get("trend_alert")

    # Deterministic prediction
    hr = vitals.get("heart_rate") or vitals.get("bpm", 72)
    spo2 = vitals.get("spo2", 98)
    hr_slope = trend.get("hr_slope", 0)
    spo2_slope = trend.get("spo2_slope", 0)

    # Simple extrapolation (5 readings ~ 15 seconds at 3s interval, ~5 min at 1min)
    projected_hr_5min = hr + hr_slope * 100
    projected_spo2_5min = spo2 + spo2_slope * 100

    det_prediction = {
        "forecast_risk": risk.get("level", "LOW"),
        "eta_critical": trend_alert or "No imminent critical trajectory",
        "confidence": 0.6 if not trend else min(0.95, 0.5 + trend.get("sample_count", 0) * 0.03),
        "projected_vitals_5min": {
            "heart_rate": round(max(30, min(250, projected_hr_5min)), 1),
            "spo2": round(max(60, min(100, projected_spo2_5min)), 1),
        },
    }

    # Ask LLM for richer prediction
    prompt = (
        f"Clinical interpretation: {interpretation}\n"
        f"Current vitals: HR={hr}, SpO2={spo2}%\n"
        f"Trend slopes: HR={hr_slope:+.2f}/reading, SpO2={spo2_slope:+.4f}/reading\n"
        f"Trend alert: {trend_alert or 'None'}\n"
        f"Patient baseline: HR={history.get('baseline_hr', '?')}, "
        f"SpO2={history.get('baseline_spo2', '?')}%\n\n"
        "Predict the short-term trajectory (5-15 min). Respond JSON:\n"
        '{"forecast_risk":"LOW|MODERATE|HIGH|CRITICAL",'
        '"eta_critical":"description of when critical might be reached",'
        '"confidence":0.0-1.0,'
        '"clinical_forecast":"1-2 sentence prediction"}'
    )

    llm_pred = await _llm_json_call(
        "You are a clinical prediction AI. Forecast patient trajectory.",
        prompt,
        det_prediction,
    )

    # Merge LLM output with deterministic
    prediction = {
        "forecast_risk": llm_pred.get("forecast_risk", det_prediction["forecast_risk"]),
        "eta_critical": llm_pred.get("eta_critical", det_prediction["eta_critical"]),
        "confidence": llm_pred.get("confidence", det_prediction["confidence"]),
        "projected_vitals_5min": det_prediction["projected_vitals_5min"],
        "clinical_forecast": llm_pred.get("clinical_forecast", ""),
    }

    trace.append({
        "step": "prediction_agent",
        "output": f"Forecast: {prediction['forecast_risk']}, Confidence: {prediction['confidence']:.0%}",
    })

    return {"prediction": prediction, "explainability_trace": trace}


# ── NODE 3: Risk Agent ────────────────────────────────────────────

async def risk_agent(state: AgentState) -> dict:
    """
    Classify severity using trends + context.
    NO hardcoded thresholds — reasons contextually.
    Uses rule engine score as baseline, may adjust up/down.
    """
    risk = state["risk_assessment"]
    interpretation = state.get("vitals_interpretation", "")
    prediction = state.get("prediction", {})
    history = state.get("patient_history", {})
    trace = list(state.get("explainability_trace", []))

    rule_score = risk.get("score", 0)
    rule_level = risk.get("level", "LOW")

    # Deterministic classification (mirrors rule engine)
    det_classification = {
        "final_level": rule_level,
        "adjusted_score": rule_score,
        "reasoning": f"Rule engine: MEWS {risk.get('mews_score', 0)}/14, "
                     f"Score {rule_score}/100. {'; '.join(risk.get('contributing_factors', [])[:2])}",
    }

    # Ask LLM to validate/adjust
    prompt = (
        f"Clinical analysis: {interpretation}\n"
        f"Prediction: {prediction.get('forecast_risk', '?')} "
        f"(confidence {prediction.get('confidence', 0):.0%})\n"
        f"Rule engine: {rule_level} ({rule_score}/100), "
        f"MEWS={risk.get('mews_score', 0)}/14\n"
        f"Factors: {', '.join(risk.get('contributing_factors', []))}\n"
        f"Trend alert: {risk.get('trend_alert') or 'None'}\n"
        f"Patient context: {history.get('conditions', 'Unknown')}\n\n"
        "Validate or adjust the risk classification. Consider trends and context. "
        "You may adjust score ±15 points based on clinical judgment. Respond JSON:\n"
        '{"final_level":"LOW|MODERATE|HIGH|CRITICAL",'
        '"adjusted_score":0-100,'
        '"reasoning":"explanation"}'
    )

    llm_class = await _llm_json_call(
        "You are a clinical risk classification AI. Validate risk scores.",
        prompt,
        det_classification,
    )

    # Safety: NEVER downgrade CRITICAL from rule engine
    final_level = llm_class.get("final_level", rule_level)
    adjusted_score = llm_class.get("adjusted_score", rule_score)

    if rule_level == "CRITICAL" and final_level != "CRITICAL":
        final_level = "CRITICAL"
        adjusted_score = max(adjusted_score, rule_score)
        llm_class["reasoning"] = (llm_class.get("reasoning", "") +
                                  " [Safety override: Rule engine CRITICAL preserved]")

    # Clamp adjusted score
    adjusted_score = max(0, min(100, int(adjusted_score)))

    classification = {
        "final_level": final_level,
        "adjusted_score": adjusted_score,
        "reasoning": llm_class.get("reasoning", det_classification["reasoning"]),
    }

    trace.append({
        "step": "risk_agent",
        "output": f"{final_level} — Score {adjusted_score}/100",
    })

    # Map to legacy fields
    condition = ("critical" if final_level == "CRITICAL"
                 else "future_alert" if final_level in ("HIGH", "MODERATE")
                 else "normal")
    severity = ("high" if final_level == "CRITICAL"
                else "medium" if final_level in ("HIGH", "MODERATE")
                else "low")

    return {
        "risk_classification": classification,
        "condition": condition,
        "severity": severity,
        "explainability_trace": trace,
    }


# ── NODE 4: Action Agent ─────────────────────────────────────────

async def action_agent(state: AgentState) -> dict:
    """
    Decide response: ignore / notify / escalate / call.
    Must include reasoning for every decision.
    Hard safety rules are deterministic — LLM only for moderate zone.
    """
    risk = state["risk_assessment"]
    classification = state.get("risk_classification", {})
    prediction = state.get("prediction", {})
    trace = list(state.get("explainability_trace", []))

    score = classification.get("adjusted_score", risk.get("score", 0))
    level = classification.get("final_level", risk.get("level", "LOW"))
    trend_alert = risk.get("trend_alert")

    # Hard deterministic rules — safety critical
    if score <= 30 and not trend_alert:
        action = "log"
        reasoning = f"Risk {score}/100 (LOW). All vitals within normal range."
        trace.append({"step": "action_agent", "rule": "deterministic_low", "output": "log"})
    elif score >= 81:
        action = "call_emergency"
        reasoning = (f"CRITICAL: MEWS {risk.get('mews_score', '?')}/14, Score {score}/100. "
                     f"Triggers: {'; '.join(risk.get('contributing_factors', [])[:3])}")
        trace.append({"step": "action_agent", "rule": "deterministic_critical", "output": "call_emergency"})
    elif score >= 61:
        action = "schedule_doctor"
        reasoning = (f"HIGH risk: Score {score}/100. Auto-scheduling medical review. "
                     f"{trend_alert or ''}")
        trace.append({"step": "action_agent", "rule": "deterministic_high", "output": "schedule_doctor"})
    elif trend_alert and score >= 50:
        action = "alert_user"
        reasoning = f"PRE-EMPTIVE: Risk {score}/100 trending upward. {trend_alert}"
        trace.append({"step": "action_agent", "rule": "preemptive_trend", "output": "alert_user"})
    else:
        # LLM for moderate zone (31-60)
        action = "alert_user" if score >= 45 else "log"
        reasoning = f"Moderate risk {score}/100. Deterministic fallback."

        prompt = (
            f"Risk classification: {level} ({score}/100)\n"
            f"Analysis: {state.get('vitals_interpretation', '')}\n"
            f"Prediction: {prediction.get('forecast_risk', '?')} "
            f"({prediction.get('clinical_forecast', '')})\n"
            f"Trend alert: {trend_alert or 'None'}\n\n"
            "Choose action: log | alert_user | schedule_doctor | call_emergency\n"
            'Respond JSON: {"action":"...","reasoning":"..."}'
        )

        llm_decision = await _llm_json_call(
            "You are a clinical action decision AI. Be conservative — when in doubt, escalate.",
            prompt,
            {"action": action, "reasoning": reasoning},
        )
        action = llm_decision.get("action", action)
        reasoning = llm_decision.get("reasoning", reasoning)
        trace.append({"step": "action_agent", "rule": "llm_moderate", "output": action})

    # Safety override: never log if MEWS >= 3
    if risk.get("mews_score", 0) >= 3 and action == "log":
        action = "alert_user"
        reasoning += " [Safety override: MEWS>=3]"

    # Map to legacy condition/severity (important for shortcut path)
    condition = ("critical" if score >= 81
                 else "future_alert" if score >= 31
                 else "normal")
    severity = ("high" if score >= 81
                else "medium" if score >= 31
                else "low")

    # Also set risk_classification if not already set (shortcut path)
    if not classification:
        classification = {
            "final_level": level,
            "adjusted_score": score,
            "reasoning": reasoning,
        }

    return {
        "decided_action": action,
        "action_reasoning": reasoning,
        "condition": condition,
        "severity": severity,
        "risk_classification": classification,
        "explainability_trace": trace,
    }


# ── NODE 5: Communication Agent ──────────────────────────────────

async def communication_agent(state: AgentState) -> dict:
    """
    Generate human-readable messages for patient and doctor.
    Patient message: calm, clear, non-alarming.
    Doctor message: precise clinical language.
    """
    vitals = state["vitals"]
    classification = state.get("risk_classification", {})
    action = state.get("decided_action", "log")
    reasoning = state.get("action_reasoning", "")
    interpretation = state.get("vitals_interpretation", "")
    prediction = state.get("prediction", {})
    trace = list(state.get("explainability_trace", []))

    level = classification.get("final_level", "LOW")
    hr = vitals.get("heart_rate") or vitals.get("bpm", 0)
    spo2 = vitals.get("spo2", 0)

    # Deterministic messages
    if level == "CRITICAL":
        det_patient = (
            "Your health readings show concerning levels. "
            "Emergency contacts are being notified. "
            "Please stay calm, sit upright, and do not exert yourself. Help is on the way."
        )
        det_doctor = (
            f"CRITICAL ALERT: HR={hr}, SpO2={spo2}%. "
            f"MEWS {state['risk_assessment'].get('mews_score', '?')}/14. "
            f"{reasoning}"
        )
    elif level in ("HIGH", "MODERATE"):
        det_patient = (
            "Some of your vitals need attention. "
            "Please take a moment to rest and monitor how you feel. "
            "A medical review has been recommended."
        )
        det_doctor = (
            f"Alert: Patient vitals elevated. HR={hr}, SpO2={spo2}%. "
            f"Score {classification.get('adjusted_score', '?')}/100. {reasoning}"
        )
    else:
        det_patient = "Your vitals look good. Keep up the healthy routine!"
        det_doctor = f"Normal reading. HR={hr}, SpO2={spo2}%. No action required."

    # LLM-enhanced messages for non-normal situations
    if level != "LOW":
        location = state.get("location", {})
        hospitals = location.get("nearest_hospitals", [])
        history = state.get("patient_history", {})
        
        prompt = (
            f"Patient vitals: {interpretation}\n"
            f"Patient history: {history}\n"
            f"Risk: {level} ({classification.get('adjusted_score', '?')}/100)\n"
            f"Action taken: {action}\n"
            f"Prediction: {prediction.get('clinical_forecast', 'N/A')}\n"
            f"Nearby Hospitals (with distance & specialization): {json.dumps(hospitals)}\n\n"
            "Task 1: Generate two messages (patient and doctor).\n"
            "Task 2: Suggest the BEST hospital from the provided list based on the patient's specific health condition (e.g. cardiac issue -> cardiology hospital) and distance. Provide a reason.\n"
            "Respond JSON:\n"
            '{"patient_message":"calm, clear 1-2 sentences for the patient",'
            '"doctor_message":"precise clinical summary for the doctor, 2-3 sentences",'
            '"recommended_hospital_name": "Name of best hospital or null",'
            '"hospital_reason": "Why this hospital was chosen"}'
        )

        msgs = await _llm_json_call(
            "You are a medical communication AI. Patient messages must be calm and reassuring. "
            "Doctor messages must be precise and clinical.",
            prompt,
            {"patient_message": det_patient, "doctor_message": det_doctor},
        )
        patient_msg = msgs.get("patient_message", det_patient)
        doctor_msg = msgs.get("doctor_message", det_doctor)
        recommended_hospital_name = msgs.get("recommended_hospital_name")
        hospital_reason = msgs.get("hospital_reason")
    else:
        patient_msg = det_patient
        doctor_msg = det_doctor
        recommended_hospital_name = None
        hospital_reason = None

    trace.append({
        "step": "communication_agent",
        "output": f"Action: {action} | Messages generated",
    })

    # ── Execute the decided action ────────────────────────────────
    action_result = await _execute_decided_action(state, action, patient_msg)

    # Build recommended actions list (legacy compat)
    actions_list = _build_actions_list(action, level)
    if recommended_hospital_name and recommended_hospital_name != "null":
        actions_list.append(f"Recommended Hospital: {recommended_hospital_name} — {hospital_reason}")

    # Build full log
    full_log = {
        "vitals": vitals,
        "risk_score": classification.get("adjusted_score", state["risk_assessment"].get("score", 0)),
        "risk_level": level,
        "mews_score": state["risk_assessment"].get("mews_score", 0),
        "trend_alert": state["risk_assessment"].get("trend_alert"),
        "trend_summary": state["risk_assessment"].get("trend_summary"),
        "contributing_factors": state["risk_assessment"].get("contributing_factors", []),
        "vitals_interpretation": interpretation,
        "prediction": prediction,
        "risk_classification": classification,
        "decided_action": action,
        "action_reasoning": reasoning,
        "patient_message": patient_msg,
        "doctor_message": doctor_msg,
        "action_result": action_result,
        "explainability_trace": trace,
    }

    return {
        "patient_message": patient_msg,
        "doctor_message": doctor_msg,
        "action_result": action_result,
        "full_log": full_log,
        "explainability_trace": trace,
        "reasoning": f"{interpretation} Action: {action}. {reasoning}",
        "actions": actions_list,
    }


def _build_actions_list(action: str, level: str) -> list:
    """Build recommended actions for the patient (legacy compat)."""
    if level == "CRITICAL":
        return [
            "Sit upright immediately to improve breathing",
            "Emergency contacts have been notified",
            "Do NOT exert yourself physically",
            "Stay where you are — help is on the way",
            "Keep this device nearby for monitoring",
        ]
    elif level == "HIGH":
        return [
            "Rest and avoid strenuous activity",
            "A doctor appointment is being scheduled",
            "Monitor your symptoms closely",
            "Stay hydrated and keep calm",
        ]
    elif level == "MODERATE":
        return [
            "Take a few minutes to rest",
            "Monitor how you feel over the next hour",
            "Contact your doctor if symptoms worsen",
        ]
    else:
        return ["Continue routine monitoring"]


async def _execute_decided_action(state: AgentState, action: str, patient_msg: str) -> dict:
    """Execute the decided action (SMS, call, email, etc.)."""
    vitals = state["vitals"]
    risk = state["risk_assessment"]
    location = state.get("location", {})
    user_id = state.get("user_id", "")
    emergency_contacts_raw = state.get("emergency_contacts", "[]")

    # Update incident state for one-shot tracking
    level = state.get("risk_classification", {}).get("final_level", risk.get("level", "LOW"))
    condition = "normal" if level == "LOW" else ("critical" if level == "CRITICAL" else "future_alert")
    update_incident_state(condition)

    if action == "log":
        return {"action_type": "log", "success": True, "message": "Reading logged"}

    if action == "alert_user":
        if try_fire("sms_patient"):
            hr = vitals.get("heart_rate") or vitals.get("bpm", "--")
            spo2 = vitals.get("spo2", "--")
            lat = location.get("lat") or state.get("location_lat")
            lng = location.get("lng") or state.get("location_lng")
            coords = get_alert_safe_coordinates(lat, lng)
            location_line = ""
            if coords:
                safe_lat, safe_lng = coords
                location_line = f"\nLive location: https://www.google.com/maps?q={safe_lat},{safe_lng}"
            sms_body = (
                f"VitalGuard Alert\n"
                f"{settings.PATIENT_NAME}\n"
                f"HR:{hr} SpO2:{spo2}%\n"
                f"Please check your vitals."
                f"{location_line}"
            )
            target = settings.PATIENT_PHONE or settings.TWILIO_TARGET_PHONE_NUMBER
            if target:
                emergency_service.trigger_sms(target, sms_body)
            return {"action_type": "alert_user", "success": True, "message": "Patient alert sent"}
        return {"action_type": "alert_user", "success": True, "message": "Alert already sent this incident"}

    if action == "schedule_doctor":
        if try_fire("email_doctor"):
            hr = vitals.get("heart_rate") or vitals.get("bpm", "--")
            subject = f"[VitalGuard] Appointment Needed - {settings.PATIENT_NAME}"
            body = (
                f"Dear Doctor,\n\n"
                f"VitalGuard has detected elevated risk for {settings.PATIENT_NAME}.\n\n"
                f"Vitals: HR={hr}, SpO2={vitals.get('spo2', '--')}%, "
                f"Temp={vitals.get('temperature', '--')}C\n"
                f"Risk: {risk.get('score', '?')}/100\n"
                f"Reasoning: {state.get('action_reasoning', '')}\n\n"
                f"Please schedule an appointment.\n\n— VitalGuard"
            )
            emergency_service.send_doctor_email(subject, body)
            return {"action_type": "schedule_doctor", "success": True, "message": "Doctor appointment scheduled"}
        return {"action_type": "schedule_doctor", "success": True, "message": "Already scheduled this incident"}

    if action == "call_emergency":
        return await _execute_emergency(state, vitals, risk, location, emergency_contacts_raw)

    return {"action_type": action, "success": True, "message": "Action processed"}


async def _execute_emergency(state, vitals, risk, location, emergency_contacts_raw) -> dict:
    """Execute emergency protocol: SMS + voice call to all contacts."""
    results = {"action_type": "call_emergency", "success": True, "sms": [], "calls": []}

    # Parse contacts
    try:
        contacts = json.loads(emergency_contacts_raw or "[]")
    except (json.JSONDecodeError, TypeError):
        contacts = []

    # Build target phone list
    seen_phones = set()
    target_phones = []

    for c in contacts:
        phone = c.get("phone")
        if phone and phone not in seen_phones:
            target_phones.append({"name": c.get("name", "Contact"), "phone": phone})
            seen_phones.add(phone)

    config_phone = settings.EMERGENCY_CONTACT_PHONE or settings.TWILIO_TARGET_PHONE_NUMBER
    if config_phone and config_phone not in seen_phones:
        target_phones.append({"name": settings.EMERGENCY_CONTACT_NAME, "phone": config_phone})

    hr = vitals.get("heart_rate") or vitals.get("bpm", "--")
    spo2 = vitals.get("spo2", "--")

    # Location
    lat = location.get("lat") or state.get("location_lat")
    lng = location.get("lng") or state.get("location_lng")
    coords = get_alert_safe_coordinates(lat, lng)
    location_line = ""
    if coords:
        safe_lat, safe_lng = coords
        location_line = f"\nLive location: https://www.google.com/maps?q={safe_lat},{safe_lng}"

    # ── SMS ──
    if try_fire("sms_emergency"):
        short_reason = state.get("action_reasoning", "Critical vitals detected")[:80]
        sms_body = (
            f"EMERGENCY VitalGuard\n"
            f"{settings.PATIENT_NAME}\n"
            f"HR:{hr} SpO2:{spo2}%\n"
            f"{short_reason}\n"
            f"Respond immediately."
            f"{location_line}"
        )
        any_success = False
        for contact in target_phones:
            result = emergency_service.trigger_sms(contact["phone"], sms_body)
            results["sms"].append({"contact": contact["name"], "result": result})
            if result.get("mode") == "live":
                any_success = True
        if not any_success and target_phones:
            unfire("sms_emergency")
    else:
        results["sms"].append({"status": "already_sent_this_incident"})

    # ── Voice Call ──
    if try_fire("voice_emergency"):
        voice_message = (
            f"Emergency alert from Vital Guard. "
            f"{settings.PATIENT_NAME} is experiencing a critical health event. "
            f"Heart rate is {hr} beats per minute. "
            f"Oxygen level is {spo2} percent. "
            f"Please respond immediately."
        )
        any_success = False
        for contact in target_phones:
            result = emergency_service.trigger_call(contact["phone"], voice_message)
            results["calls"].append({"contact": contact["name"], "result": result})
            if result.get("mode") == "live":
                any_success = True
        if not any_success and target_phones:
            unfire("voice_emergency")
    else:
        results["calls"].append({"status": "already_called_this_incident"})

    # ── Doctor Email ──
    if try_fire("email_doctor"):
        subject = f"[VitalGuard] CRITICAL - {settings.PATIENT_NAME}"
        body = (
            f"Dear Doctor,\n\n"
            f"CRITICAL health event for {settings.PATIENT_NAME}.\n"
            f"HR={hr}, SpO2={spo2}%\n"
            f"Emergency contacts notified.\n\n— VitalGuard"
        )
        emergency_service.send_doctor_email(subject, body)

    results["message"] = f"Emergency protocol executed — {len(target_phones)} contacts notified"
    return results
