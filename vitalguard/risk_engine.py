"""
VitalGuard — Clinical Risk Scoring Engine v2
Implements evidence-based scoring:

  1. Modified Early Warning Score (MEWS) — validated deterioration predictor
     Ref: Subbe et al., 2001, QJM
  2. Trend-adjusted risk: slope x velocity penalty
  3. Predictive alert: projects crossing time for thresholds
  4. LLM validation via Ollama llama3.1:8b (free, local, no API key needed)
     Falls back gracefully to deterministic if Ollama is not running.

Risk levels:  LOW (0-30) | MODERATE (31-60) | HIGH (61-80) | CRITICAL (81-100)
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Literal, Optional

from simulator import VitalSigns, VitalHistory

logger = logging.getLogger("vitalguard.risk_engine")

RiskLevel = Literal["LOW", "MODERATE", "HIGH", "CRITICAL"]

# ── MEWS Thresholds (NHS NEWS2 + Subbe et al., 2001) ─────────────

MEWS_HEART_RATE = [
    (0,   40,   3), (40,  50,   2), (50,  100,  0),
    (100, 110,  1), (110, 130,  2), (130, 999,  3),
]
MEWS_SPO2 = [
    (0, 84, 3), (84, 88, 2), (88, 92, 1), (92, 94, 1), (94, 100, 0),
]
MEWS_TEMP = [
    (0, 35.0, 2), (35.0, 36.0, 1), (36.0, 38.0, 0),
    (38.0, 38.5, 1), (38.5, 39.5, 2), (39.5, 99.0, 3),
]
MEWS_HRV = [
    (0, 8, 3), (8, 15, 2), (15, 20, 1), (20, 70, 0), (70, 999, 0),
]


def _score_band(value: float, bands: list) -> int:
    for lo, hi, pts in bands:
        if lo <= value < hi:
            return pts
    return 0


def _mews_score(vitals: VitalSigns) -> tuple[int, list[str]]:
    factors = []
    total = 0

    hr_pts = _score_band(vitals.heart_rate, MEWS_HEART_RATE)
    if hr_pts >= 2:
        label = ("critically high" if vitals.heart_rate >= 130
                 else "elevated" if vitals.heart_rate >= 110
                 else "critically low" if vitals.heart_rate < 40 else "low")
        factors.append(f"Heart rate {label} ({vitals.heart_rate:.0f} bpm) +{hr_pts}")
    elif hr_pts == 1:
        factors.append(f"Heart rate mildly elevated ({vitals.heart_rate:.0f} bpm) +1")
    total += hr_pts

    spo2_pts = _score_band(vitals.spo2, MEWS_SPO2)
    if spo2_pts > 0:
        sev = "critically" if spo2_pts >= 2 else "mildly"
        factors.append(f"SpO2 {sev} low ({vitals.spo2:.1f}%) +{spo2_pts}")
    total += spo2_pts

    temp_pts = _score_band(vitals.temperature, MEWS_TEMP)
    if temp_pts > 0:
        direction = "high" if vitals.temperature > 38.0 else "low"
        factors.append(f"Temperature {'critically' if temp_pts >= 2 else 'mildly'} {direction} ({vitals.temperature:.1f}C) +{temp_pts}")
    total += temp_pts

    hrv_pts = _score_band(vitals.hrv, MEWS_HRV)
    if hrv_pts > 0:
        factors.append(f"HRV reduced ({vitals.hrv:.1f} ms, autonomic stress) +{hrv_pts}")
    total += hrv_pts

    return total, factors


# ── Risk Assessment Dataclass ─────────────────────────────────────

@dataclass
class RiskAssessment:
    score: int
    level: RiskLevel
    contributing_factors: list[str] = field(default_factory=list)
    summary: str = ""
    mews_score: int = 0
    trend_alert: Optional[str] = None
    trend_summary: Optional[dict] = None
    validated_by: str = "deterministic"

    def to_dict(self) -> dict:
        return {
            "score": self.score,
            "level": self.level,
            "contributing_factors": self.contributing_factors,
            "summary": self.summary,
            "mews_score": self.mews_score,
            "trend_alert": self.trend_alert,
            "trend_summary": self.trend_summary,
            "validated_by": self.validated_by,
        }


# ── Deterministic Compute (always runs, never fails) ─────────────

def _deterministic_compute(vitals: VitalSigns, history: Optional[VitalHistory] = None) -> RiskAssessment:
    mews, factors = _mews_score(vitals)

    score_map = {0: 5, 1: 18, 2: 32, 3: 50, 4: 65, 5: 75, 6: 82, 7: 88, 8: 92}
    base_score = score_map.get(mews, 95 if mews > 8 else 5)

    flagged = len(factors)
    if flagged >= 3:
        base_score = min(100, int(base_score * 1.25))
        factors.append("Multiple concurrent abnormalities — compounding risk")
    elif flagged == 2:
        base_score = min(100, int(base_score * 1.12))

    trend_alert = None
    trend_summary = None

    if history is not None:
        trend_summary = history.trend_summary(n=10)
        hr_s   = trend_summary.get("hr_slope", 0)
        spo2_s = trend_summary.get("spo2_slope", 0)
        temp_s = trend_summary.get("temp_slope", 0)

        if hr_s > 1.5:
            base_score = min(100, base_score + min(15, int(hr_s * 3)))
            factors.append(f"HR rising trend (+{hr_s:.1f} bpm/s)")
        if spo2_s < -0.05:
            base_score = min(100, base_score + min(20, int(abs(spo2_s) * 80)))
            factors.append(f"SpO2 declining trend ({spo2_s:.3f}%/s)")
        if temp_s > 0.02:
            base_score = min(100, base_score + min(10, int(temp_s * 150)))
            factors.append(f"Temperature rising trend (+{temp_s:.3f}C/s)")

        alerts = []
        if vitals.heart_rate < 135 and hr_s > 0:
            eta = history.predict_crossing("heart_rate", 140, n=12)
            if eta and 0 < eta < 60:
                alerts.append(f"HR projected critical in ~{eta}s")
        if vitals.spo2 > 88 and spo2_s < 0:
            eta = history.predict_crossing("spo2", 88, n=12)
            if eta and 0 < eta < 60:
                alerts.append(f"SpO2 projected critical in ~{eta}s")
        if vitals.temperature < 39.0 and temp_s > 0:
            eta = history.predict_crossing("temperature", 39.5, n=12)
            if eta and 0 < eta < 90:
                alerts.append(f"Fever projected critical in ~{eta}s")
        if alerts:
            trend_alert = " | ".join(alerts)

    base_score = max(0, min(100, base_score))

    if base_score >= 81:
        level: RiskLevel = "CRITICAL"
    elif base_score >= 61:
        level = "HIGH"
    elif base_score >= 31:
        level = "MODERATE"
    else:
        level = "LOW"

    summary = (
        "All vitals within normal range. No clinical concerns detected."
        if not factors
        else f"MEWS {mews}/12 - Risk {base_score}/100 ({level}). {'; '.join(f.split('+')[0].strip() for f in factors[:3])}."
    )
    if trend_alert:
        summary += f" TREND: {trend_alert}"

    return RiskAssessment(
        score=base_score, level=level,
        contributing_factors=factors, summary=summary,
        mews_score=mews, trend_alert=trend_alert,
        trend_summary=trend_summary, validated_by="deterministic",
    )


# ── LLM Validation (Ollama llama3.1:8b — free, local) ────────────

async def compute_risk(vitals: VitalSigns, history: Optional[VitalHistory] = None) -> RiskAssessment:
    baseline = _deterministic_compute(vitals, history)

    # Skip LLM for clearly normal readings to save latency
    if baseline.score < 25:
        return baseline

    trend = baseline.trend_summary or {}
    trend_text = ""
    if trend:
        trend_text = (
            f"\nTrend (last 10 readings):"
            f" HR={trend.get('hr_slope',0):+.2f} bpm/s,"
            f" SpO2={trend.get('spo2_slope',0):+.4f}%/s,"
            f" Temp={trend.get('temp_slope',0):+.4f}C/s"
        )
        if baseline.trend_alert:
            trend_text += f"\nAlert: {baseline.trend_alert}"

    prompt = (
        f"Clinical risk AI. Patient: {vitals.patient_label}\n"
        f"HR={vitals.heart_rate:.1f}bpm SpO2={vitals.spo2:.1f}% "
        f"Temp={vitals.temperature:.1f}C HRV={vitals.hrv:.1f}ms\n"
        f"MEWS={baseline.mews_score}/12 RuleScore={baseline.score}/100 ({baseline.level})\n"
        f"Flags: {', '.join(baseline.contributing_factors) or 'None'}"
        f"{trend_text}\n\n"
        "Validate or adjust. Respond ONLY valid JSON, no markdown:\n"
        '{"score":<int>,"level":"<LOW|MODERATE|HIGH|CRITICAL>","factors":["..."],"summary":"..."}'
    )

    try:
        from langchain_ollama import ChatOllama
        from langchain_core.messages import SystemMessage, HumanMessage

        llm = ChatOllama(
            model="llama3.1:8b",
            temperature=0.1,
            num_predict=280,
            base_url="http://127.0.0.1:11434",
        )
        response = await llm.ainvoke([
            SystemMessage(content="Clinical risk AI. Respond ONLY in valid JSON, no markdown fences."),
            HumanMessage(content=prompt),
        ])
        text = response.content.strip().replace("```json", "").replace("```", "").strip()
        start, end = text.find("{"), text.rfind("}") + 1
        if start == -1 or end == 0:
            raise ValueError("No JSON found in LLM response")
        parsed = json.loads(text[start:end])

        return RiskAssessment(
            score=max(0, min(100, int(parsed.get("score", baseline.score)))),
            level=parsed.get("level", baseline.level),
            contributing_factors=parsed.get("factors", baseline.contributing_factors),
            summary=parsed.get("summary", baseline.summary),
            mews_score=baseline.mews_score,
            trend_alert=baseline.trend_alert,
            trend_summary=baseline.trend_summary,
            validated_by="llama3.1",
        )

    except Exception as e:
        logger.warning(f"Ollama unavailable ({type(e).__name__}). Using deterministic MEWS score.")
        return baseline
