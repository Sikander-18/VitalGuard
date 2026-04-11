"""
VitalGuard — LangGraph Agent Pipeline v2
4-node clinical reasoning chain:
  vitals_analyzer -> anomaly_detector -> decision_maker -> action_executor

AI: Ollama llama3.1:8b (free, local, no API key needed)
Gracefully falls back to deterministic rules if Ollama is not running.
"""

import json
import logging
from typing import Optional, TypedDict

from langgraph.graph import StateGraph, END
from actions import execute_action

logger = logging.getLogger("vitalguard.agents")


# ── LLM Factory (Ollama only — free & local) ─────────────────────

def get_llm():
    try:
        from langchain_ollama import ChatOllama
        return ChatOllama(
            model="llama3.1:8b",
            temperature=0.3,
            num_predict=350,
            base_url="http://127.0.0.1:11434",
        )
    except Exception as e:
        logger.warning(f"Ollama init failed: {e}")
        return None


# ── Agent State ───────────────────────────────────────────────────

class AgentState(TypedDict):
    vitals: dict
    risk: dict
    location: dict
    trend_context: str
    clinical_analysis: str
    anomaly_assessment: str
    decided_action: str
    action_reasoning: str
    action_result: dict
    full_log: dict
    explainability_trace: list


# ── Trend context builder ─────────────────────────────────────────

def _build_trend_context(risk: dict) -> str:
    trend = risk.get("trend_summary") or {}
    alert = risk.get("trend_alert")
    if not trend:
        return "No trend data yet (< 3 readings)."
    lines = [
        f"HR trend: {trend.get('hr_slope', 0):+.2f} bpm/reading",
        f"SpO2 trend: {trend.get('spo2_slope', 0):+.4f}%/reading",
        f"Temp trend: {trend.get('temp_slope', 0):+.4f}C/reading",
        f"HRV trend: {trend.get('hrv_slope', 0):+.2f} ms/reading",
    ]
    if alert:
        lines.append(f"PREDICTIVE ALERT: {alert}")
    return "\n".join(lines)


# ── Node 1: Vitals Analyzer ───────────────────────────────────────

async def vitals_analyzer(state: AgentState) -> dict:
    vitals = state["vitals"]
    risk   = state["risk"]
    trend  = state.get("trend_context", "")
    trace  = state.get("explainability_trace", [])

    prompt = (
        f"Clinical monitoring AI. Patient: {vitals.get('patient_label', 'Unknown')}\n"
        f"HR={vitals['heart_rate']}bpm SpO2={vitals['spo2']}% "
        f"Temp={vitals['temperature']}C HRV={vitals['hrv']}ms\n"
        f"MEWS={risk.get('mews_score','?')}/12 Risk={risk['score']}/100 ({risk['level']})\n"
        f"Flags: {', '.join(risk.get('contributing_factors', [])) or 'None'}\n"
        f"Trends:\n{trend}\n\n"
        "Write a concise 2-3 sentence clinical interpretation."
    )

    analysis = _fallback_analysis(vitals, risk)
    llm = get_llm()
    if llm:
        try:
            from langchain_core.messages import SystemMessage, HumanMessage
            response = await llm.ainvoke([
                SystemMessage(content="Medical AI. Be concise and clinically precise."),
                HumanMessage(content=prompt),
            ])
            analysis = response.content
        except Exception as e:
            logger.warning(f"Vitals analyzer LLM failed: {e}")

    trace.append({
        "step": "vitals_analyzer",
        "input_summary": f"HR={vitals['heart_rate']}, SpO2={vitals['spo2']}%, T={vitals['temperature']}C",
        "output": analysis[:220],
    })
    return {"clinical_analysis": analysis, "explainability_trace": trace}


def _fallback_analysis(vitals, risk):
    return (
        f"[Deterministic] HR={vitals['heart_rate']:.0f}bpm, "
        f"SpO2={vitals['spo2']:.1f}%, Temp={vitals['temperature']:.1f}C, "
        f"HRV={vitals['hrv']:.1f}ms. MEWS={risk.get('mews_score','?')} "
        f"Risk {risk['score']}/100 ({risk['level']})."
    )


# ── Node 2: Anomaly Detector ──────────────────────────────────────

async def anomaly_detector(state: AgentState) -> dict:
    risk  = state["risk"]
    trace = state.get("explainability_trace", [])

    if risk["score"] <= 30:
        trace.append({"step": "anomaly_detector", "output": "Skipped — risk score ≤30"})
        return {"anomaly_assessment": "No significant anomalies. Vitals within normal range.",
                "explainability_trace": trace}

    prompt = (
        f"Medical anomaly detection AI.\n"
        f"Clinical: {state['clinical_analysis']}\n"
        f"Risk={risk['score']}/100 ({risk['level']}) MEWS={risk.get('mews_score','?')}/12\n"
        f"Trend alert: {risk.get('trend_alert') or 'None'}\n\n"
        "Is this a genuine clinical deterioration? How urgent? 2-3 sentences."
    )

    assessment = f"Risk {risk['score']}/100 ({risk['level']}). Factors: {'; '.join(risk.get('contributing_factors', []))}"
    llm = get_llm()
    if llm:
        try:
            from langchain_core.messages import SystemMessage, HumanMessage
            response = await llm.ainvoke([
                SystemMessage(content="Medical anomaly AI. Be direct and clinically accurate."),
                HumanMessage(content=prompt),
            ])
            assessment = response.content
        except Exception as e:
            logger.warning(f"Anomaly detector LLM failed: {e}")

    trace.append({"step": "anomaly_detector", "output": assessment[:220]})
    return {"anomaly_assessment": assessment, "explainability_trace": trace}


# ── Node 3: Decision Maker ────────────────────────────────────────

async def decision_maker(state: AgentState) -> dict:
    risk   = state["risk"]
    score  = risk["score"]
    trace  = state.get("explainability_trace", [])
    trend_alert = risk.get("trend_alert")

    # Hard deterministic rules — safety-critical, never handed to LLM
    if score <= 30 and not trend_alert:
        trace.append({"step": "decision_maker", "rule": "deterministic_low", "output": "log"})
        return {"decided_action": "log",
                "action_reasoning": f"Risk {score}/100 (LOW). All vitals normal.",
                "explainability_trace": trace}

    if score >= 81:
        reasoning = (f"CRITICAL: MEWS {risk.get('mews_score','?')}/12, Risk {score}/100. "
                     f"Triggers: {'; '.join(risk.get('contributing_factors', []))}")
        trace.append({"step": "decision_maker", "rule": "deterministic_critical", "output": "call_emergency"})
        return {"decided_action": "call_emergency", "action_reasoning": reasoning,
                "explainability_trace": trace}

    if score >= 61:
        reasoning = (f"HIGH risk: MEWS {risk.get('mews_score','?')}/12, Risk {score}/100. "
                     f"Auto-scheduling medical review. {risk.get('trend_alert') or ''}")
        trace.append({"step": "decision_maker", "rule": "deterministic_high", "output": "schedule_doctor"})
        return {"decided_action": "schedule_doctor", "action_reasoning": reasoning,
                "explainability_trace": trace}

    if trend_alert and score >= 50:
        reasoning = f"PRE-EMPTIVE: Risk {score}/100 trending critical. {trend_alert}"
        trace.append({"step": "decision_maker", "rule": "preemptive_trend", "output": "alert_user"})
        return {"decided_action": "alert_user", "action_reasoning": reasoning,
                "explainability_trace": trace}

    # LLM for moderate zone (31-60)
    action    = "alert_user" if score >= 45 else "log"
    reasoning = f"Moderate risk {score}/100. Deterministic fallback."

    llm = get_llm()
    if llm:
        prompt = (
            f"Clinical decision AI.\n"
            f"Analysis: {state['clinical_analysis']}\n"
            f"Anomaly: {state['anomaly_assessment']}\n"
            f"Risk={score}/100 ({risk['level']}) Trend alert: {trend_alert or 'None'}\n\n"
            "Choose action: log | alert_user | schedule_doctor | call_emergency\n"
            'Respond ONLY JSON: {"action":"...","reasoning":"..."}'
        )
        try:
            from langchain_core.messages import SystemMessage, HumanMessage
            response = await llm.ainvoke([
                SystemMessage(content="Clinical decision AI. Respond ONLY valid JSON."),
                HumanMessage(content=prompt),
            ])
            text = response.content.strip().replace("```json", "").replace("```", "").strip()
            start, end = text.find("{"), text.rfind("}") + 1
            parsed    = json.loads(text[start:end])
            action    = parsed.get("action", action)
            reasoning = parsed.get("reasoning", reasoning)
        except Exception as e:
            logger.warning(f"Decision maker LLM failed: {e}")

    # Safety override: never log if MEWS >= 3
    if risk.get("mews_score", 0) >= 3 and action == "log":
        action    = "alert_user"
        reasoning += " [Safety override: MEWS>=3]"

    trace.append({"step": "decision_maker", "rule": "llm_moderate", "output": action})
    return {"decided_action": action, "action_reasoning": reasoning,
            "explainability_trace": trace}


# ── Node 4: Action Executor ───────────────────────────────────────

async def action_executor(state: AgentState) -> dict:
    action_type    = state["decided_action"]
    vitals         = state["vitals"]
    risk           = state["risk"]
    reasoning      = state["action_reasoning"]
    location       = state.get("location", {"lat": None, "lng": None})
    trigger_vitals = risk.get("contributing_factors", [])
    trace          = state.get("explainability_trace", [])

    result = await execute_action(action_type, vitals, risk, reasoning, location, trigger_vitals)
    result_dict = result.to_dict()

    if action_type == "call_emergency":
        contact = await execute_action("notify_contact", vitals, risk, reasoning, location, trigger_vitals)
        result_dict["contact_notification"] = contact.to_dict()

    trace.append({"step": "action_executor", "action": action_type,
                  "result": result_dict.get("message", "")})

    full_log = {
        "vitals": vitals,
        "risk_score": risk.get("score"),
        "risk_level": risk.get("level"),
        "mews_score": risk.get("mews_score"),
        "trend_alert": risk.get("trend_alert"),
        "trend_summary": risk.get("trend_summary"),
        "trigger_vitals": risk.get("contributing_factors", []),
        "clinical_analysis": state.get("clinical_analysis", ""),
        "anomaly_assessment": state.get("anomaly_assessment", ""),
        "decided_action": action_type,
        "action_reasoning": reasoning,
        "action_result": result_dict,
        "explainability_trace": trace,
        "validated_by": risk.get("validated_by", "deterministic"),
    }
    return {"action_result": result_dict, "full_log": full_log,
            "explainability_trace": trace}


# ── Graph ─────────────────────────────────────────────────────────

def should_skip_anomaly(state: AgentState) -> str:
    return "decision_maker" if state["risk"]["score"] <= 30 else "anomaly_detector"


def build_agent_graph():
    graph = StateGraph(AgentState)
    graph.add_node("vitals_analyzer",  vitals_analyzer)
    graph.add_node("anomaly_detector", anomaly_detector)
    graph.add_node("decision_maker",   decision_maker)
    graph.add_node("action_executor",  action_executor)
    graph.set_entry_point("vitals_analyzer")
    graph.add_conditional_edges(
        "vitals_analyzer", should_skip_anomaly,
        {"anomaly_detector": "anomaly_detector", "decision_maker": "decision_maker"},
    )
    graph.add_edge("anomaly_detector", "decision_maker")
    graph.add_edge("decision_maker",   "action_executor")
    graph.add_edge("action_executor",  END)
    return graph.compile()


agent = build_agent_graph()


# ── Entry point ───────────────────────────────────────────────────

async def run_agent(vitals: dict, risk: dict, location: Optional[dict] = None):
    if location is None:
        location = {"lat": None, "lng": None}

    initial_state: AgentState = {
        "vitals": vitals,
        "risk": risk,
        "location": location,
        "trend_context": _build_trend_context(risk),
        "clinical_analysis": "",
        "anomaly_assessment": "",
        "decided_action": "",
        "action_reasoning": "",
        "action_result": {},
        "full_log": {},
        "explainability_trace": [],
    }
    result = await agent.ainvoke(initial_state)
    return result.get("full_log", result)
