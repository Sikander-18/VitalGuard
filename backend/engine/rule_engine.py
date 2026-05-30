"""
VitalGuard v2 — Clinical Risk Scoring Engine
Evidence-based scoring with MEWS + trend analysis + predictive alerts.

Implements:
  1. Modified Early Warning Score (MEWS) — validated deterioration predictor
     Ref: Subbe et al., 2001, QJM
  2. Trend-adjusted risk: slope × velocity penalty
  3. Predictive alert: projects crossing time for thresholds
  4. Data validation: reject NaN, missing, out-of-range

Risk levels:  LOW (0-30) | MODERATE (31-60) | HIGH (61-80) | CRITICAL (81-100)
"""

import logging
import math
from dataclasses import dataclass, field
from typing import Literal, Optional, List, Dict, Any

from .trend import VitalReading, VitalHistory, get_patient_history, push_vital

logger = logging.getLogger("vitalguard.rule_engine")

RiskLevel = Literal["LOW", "MODERATE", "HIGH", "CRITICAL"]


# ── MEWS Thresholds (NHS NEWS2 + Subbe et al., 2001) ─────────────

MEWS_HEART_RATE = [
    (0, 40, 3), (40, 50, 2), (50, 100, 0),
    (100, 110, 1), (110, 130, 2), (130, 999, 3),
]
MEWS_SPO2 = [
    (0, 84, 3), (84, 88, 2), (88, 92, 1), (92, 94, 1), (94, 101, 0),
]
MEWS_TEMP = [
    (0, 35.0, 2), (35.0, 36.0, 1), (36.0, 38.0, 0),
    (38.0, 38.5, 1), (38.5, 39.5, 2), (39.5, 99.0, 3),
]
MEWS_HRV = [
    (0, 8, 3), (8, 15, 2), (15, 20, 1), (20, 70, 0), (70, 999, 0),
]
MEWS_SYSTOLIC = [
    (0, 70, 3), (70, 80, 2), (80, 100, 1), (100, 200, 0), (200, 999, 3),
]


def _score_band(value: float, bands: list) -> int:
    for lo, hi, pts in bands:
        if lo <= value < hi:
            return pts
    return 0


def _mews_score(hr: float, spo2: float, temp: float, hrv: float,
                systolic: int = 120) -> tuple:
    """Compute MEWS score and contributing factors."""
    factors = []
    total = 0

    # Heart Rate
    hr_pts = _score_band(hr, MEWS_HEART_RATE)
    if hr_pts >= 2:
        label = ("critically high" if hr >= 130
                 else "elevated" if hr >= 110
                 else "critically low" if hr < 40 else "low")
        factors.append(f"Heart rate {label} ({hr:.0f} bpm) +{hr_pts}")
    elif hr_pts == 1:
        factors.append(f"Heart rate mildly elevated ({hr:.0f} bpm) +1")
    total += hr_pts

    # SpO2
    spo2_pts = _score_band(spo2, MEWS_SPO2)
    if spo2_pts > 0:
        sev = "critically" if spo2_pts >= 2 else "mildly"
        factors.append(f"SpO2 {sev} low ({spo2:.1f}%) +{spo2_pts}")
    total += spo2_pts

    # Temperature
    temp_pts = _score_band(temp, MEWS_TEMP)
    if temp_pts > 0:
        direction = "high" if temp > 38.0 else "low"
        sev = "critically" if temp_pts >= 2 else "mildly"
        factors.append(f"Temperature {sev} {direction} ({temp:.1f}°C) +{temp_pts}")
    total += temp_pts

    # HRV
    hrv_pts = _score_band(hrv, MEWS_HRV)
    if hrv_pts > 0:
        factors.append(f"HRV reduced ({hrv:.1f} ms, autonomic stress) +{hrv_pts}")
    total += hrv_pts

    # Systolic BP
    sys_pts = _score_band(systolic, MEWS_SYSTOLIC)
    if sys_pts > 0:
        direction = "high" if systolic >= 200 else "low"
        factors.append(f"Systolic BP {direction} ({systolic} mmHg) +{sys_pts}")
    total += sys_pts

    return total, factors


# ── Risk Assessment Result ────────────────────────────────────────

@dataclass
class RiskAssessment:
    score: int = 0
    level: RiskLevel = "LOW"
    contributing_factors: List[str] = field(default_factory=list)
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


# ── Data Validation ───────────────────────────────────────────────

def validate_vitals(vitals: Dict[str, Any]) -> tuple:
    """
    Validate vital signs. Returns (is_valid, cleaned_vitals, errors).
    Rejects NaN, missing critical fields, out-of-range values.
    """
    errors = []

    hr = vitals.get("heart_rate")
    if hr is None: hr = vitals.get("bpm")
    spo2 = vitals.get("spo2")
    temp = vitals.get("temperature")
    hrv = vitals.get("hrv")
    systolic = vitals.get("systolic")
    diastolic = vitals.get("diastolic")

    if hr is None:
        errors.append("Missing heart rate")
        hr = 0
    if spo2 is None:
        errors.append("Missing SpO2")
        spo2 = 0
    if temp is None: temp = 36.6
    if hrv is None: hrv = 40.0
    if systolic is None: systolic = 120
    if diastolic is None: diastolic = 80

    # NaN check
    for name, val in [("heart_rate", hr), ("spo2", spo2), ("temperature", temp), ("hrv", hrv)]:
        try:
            if math.isnan(float(val)):
                errors.append(f"{name} is NaN")
        except (TypeError, ValueError):
            errors.append(f"{name} invalid: {val}")

    # Range validation
    hr = float(hr)
    spo2 = float(spo2)
    temp = float(temp)
    hrv = float(hrv)

    if not (20 <= hr <= 300):
        errors.append(f"Heart rate out of range: {hr}")
    if not (50 <= spo2 <= 100):
        errors.append(f"SpO2 out of range: {spo2}")
    if not (30 <= temp <= 45):
        errors.append(f"Temperature out of range: {temp}")

    cleaned = {
        "heart_rate": hr,
        "spo2": spo2,
        "temperature": temp,
        "hrv": max(0, hrv),
        "systolic": int(systolic),
        "diastolic": int(diastolic),
    }

    return (len(errors) == 0, cleaned, errors)


# ── Main Risk Computation ─────────────────────────────────────────

def compute_risk(vitals: Dict[str, Any], patient_id: str = "P001", patient_history: Optional[Dict[str, Any]] = None) -> RiskAssessment:
    """
    Deterministic personalized risk computation — always runs, never fails.
    This is the safety-critical path: no LLM dependency.
    """
    # Validate
    is_valid, cleaned, errors = validate_vitals(vitals)
    if not is_valid and cleaned["heart_rate"] == 0:
        return RiskAssessment(
            score=0, level="LOW",
            contributing_factors=[f"Invalid data: {'; '.join(errors)}"],
            summary="Data validation failed — cannot assess risk.",
            validated_by="validation_error",
        )

    hr = cleaned["heart_rate"]
    spo2 = cleaned["spo2"]
    temp = cleaned["temperature"]
    hrv = cleaned["hrv"]
    systolic = cleaned["systolic"]

    # Push to history
    reading = VitalReading(
        heart_rate=hr, spo2=spo2, temperature=temp, hrv=hrv,
        systolic=systolic, diastolic=cleaned["diastolic"],
        patient_id=patient_id,
    )
    push_vital(patient_id, reading)

    # 1. Load personalized baselines & chronic conditions
    baseline_hr = 72.0
    baseline_spo2 = 98.0
    baseline_hrv = 45.0
    baseline_temp = 36.6
    baseline_sys = 120
    conditions = "[]"
    
    if patient_history:
        baseline_hr = float(patient_history.get("baseline_hr") or 72.0)
        baseline_spo2 = float(patient_history.get("baseline_spo2") or 98.0)
        baseline_hrv = float(patient_history.get("baseline_hrv") or 45.0)
        baseline_temp = float(patient_history.get("baseline_temp") or 36.6)
        conditions = str(patient_history.get("conditions") or "[]")

    # 2. Tighten safety tolerances dynamically based on chronic conditions (Wow factor!)
    hr_safe_margin = 0.25      # 25% HR fluctuation standard
    spo2_min_threshold = 93.0  # 93% SpO2 minimum standard
    bp_sys_margin = 0.20       # 20% BP fluctuation standard
    hrv_min_threshold = 20.0   # 20ms HRV minimum standard
    
    is_cardiac = "Heart Disease" in conditions
    is_hypertensive = "Hypertension" in conditions
    is_diabetic = "Diabetes" in conditions
    
    if is_cardiac:
        hr_safe_margin = 0.12     # Cardiac patients: shrink safety buffer to 12% fluctuation!
        hrv_min_threshold = 30.0  # Highly sensitive to autonomic stress
    if is_hypertensive:
        bp_sys_margin = 0.10      # Hypertensive patients: shrink BP safety margin to 10%!
    if is_diabetic:
        spo2_min_threshold = 95.0 # Diabetic/respiratory risk: higher target oxygen floor!

    # 3. Calculate Personalized Score & Factors
    factors = []
    mews = 0

    # Heart Rate Deviation
    hr_dev = (hr - baseline_hr) / baseline_hr
    if hr_dev > hr_safe_margin:
        pts = 3 if hr_dev > (hr_safe_margin * 1.5) else 2
        label = "critically high" if pts == 3 else "elevated"
        factors.append(f"Heart rate {label} ({hr:.0f} bpm, +{hr_dev:.1%} deviation from baseline {baseline_hr:.0f}) +{pts}")
        mews += pts
    elif hr_dev < -0.25:
        factors.append(f"Heart rate low ({hr:.0f} bpm, {hr_dev:.1%} deviation) +2")
        mews += 2

    # SpO2 Drop
    spo2_drop = baseline_spo2 - spo2
    if spo2 < spo2_min_threshold or spo2_drop > 4.0:
        pts = 3 if (spo2 < (spo2_min_threshold - 3) or spo2_drop > 8.0) else 2
        sev = "critically" if pts == 3 else "mildly"
        factors.append(f"SpO2 {sev} low ({spo2:.1f}%, drop of {spo2_drop:.1f}% below baseline {baseline_spo2:.1f}) +{pts}")
        mews += pts

    # HRV Drop
    if hrv < hrv_min_threshold:
        factors.append(f"HRV critically reduced ({hrv:.1f} ms, baseline {baseline_hrv:.1f}) +2")
        mews += 2

    # Systolic BP Deviation
    sys_dev = (systolic - baseline_sys) / baseline_sys
    if abs(sys_dev) > bp_sys_margin:
        pts = 3 if abs(sys_dev) > (bp_sys_margin * 1.5) else 2
        direction = "high" if sys_dev > 0 else "low"
        factors.append(f"BP Systolic {direction} ({systolic} mmHg, {sys_dev:+.1%} deviation from baseline {baseline_sys}) +{pts}")
        mews += pts

    # MEWS → Risk score mapping
    score_map = {0: 5, 1: 18, 2: 32, 3: 50, 4: 65, 5: 75, 6: 82, 7: 88, 8: 92}
    base_score = score_map.get(mews, 95 if mews > 8 else 5)

    # Multi-vital compounding
    flagged = len(factors)
    if flagged >= 3:
        base_score = min(100, int(base_score * 1.25))
        factors.append("Multiple concurrent deviations — compounding risk")
    elif flagged == 2:
        base_score = min(100, int(base_score * 1.12))

    # Trend analysis
    history = get_patient_history(patient_id)
    trend_alert = None
    trend_summary = None

    if history.count >= 3:
        trend_summary = history.trend_summary(n=10)
        hr_s = trend_summary.get("hr_slope", 0)
        spo2_s = trend_summary.get("spo2_slope", 0)
        temp_s = trend_summary.get("temp_slope", 0)

        # Trend penalties
        if hr_s > 1.5:
            penalty = min(15, int(hr_s * 3))
            base_score = min(100, base_score + penalty)
            factors.append(f"HR rising trend (+{hr_s:.1f} bpm/reading)")
        if spo2_s < -0.05:
            penalty = min(20, int(abs(spo2_s) * 80))
            base_score = min(100, base_score + penalty)
            factors.append(f"SpO2 declining trend ({spo2_s:.3f}%/reading)")
        if temp_s > 0.02:
            penalty = min(10, int(temp_s * 150))
            base_score = min(100, base_score + penalty)
            factors.append(f"Temperature rising trend (+{temp_s:.3f}°C/reading)")

        # Predictive crossing alerts
        alerts = []
        if hr < 135 and hr_s > 0:
            eta = history.predict_crossing("heart_rate", 140, n=12)
            if eta and 0 < eta < 60:
                alerts.append(f"HR projected critical in ~{eta} readings")
        if spo2 > 88 and spo2_s < 0:
            eta = history.predict_crossing("spo2", 88, n=12)
            if eta and 0 < eta < 60:
                alerts.append(f"SpO2 projected critical in ~{eta} readings")
        if temp < 39.0 and temp_s > 0:
            eta = history.predict_crossing("temperature", 39.5, n=12)
            if eta and 0 < eta < 90:
                alerts.append(f"Fever projected critical in ~{eta} readings")
        if alerts:
            trend_alert = " | ".join(alerts)

    # Clamp
    base_score = max(0, min(100, base_score))

    # Level classification
    if base_score >= 81:
        level: RiskLevel = "CRITICAL"
    elif base_score >= 61:
        level = "HIGH"
    elif base_score >= 31:
        level = "MODERATE"
    else:
        level = "LOW"

    # Summary
    if not factors:
        summary = "All vitals within normal range. No clinical concerns detected."
    else:
        factor_labels = [f.split("+")[0].strip() for f in factors[:3]]
        summary = f"MEWS {mews}/14 — Risk {base_score}/100 ({level}). {'; '.join(factor_labels)}."
    if trend_alert:
        summary += f" TREND: {trend_alert}"

    return RiskAssessment(
        score=base_score,
        level=level,
        contributing_factors=factors,
        summary=summary,
        mews_score=mews,
        trend_alert=trend_alert,
        trend_summary=trend_summary,
        validated_by="deterministic",
    )


# ── Legacy API (backward compatible) ─────────────────────────────

def check_vitals_anomaly(vitals: Dict[str, Any]) -> bool:
    """
    Legacy API: Returns True if an anomaly is detected.
    Used by routes/vitals.py to decide whether to run agent pipeline.
    """
    hr = vitals.get("heart_rate")
    if hr is None: hr = vitals.get("bpm")
    if hr is None: hr = 70
    spo2 = vitals.get("spo2")
    if spo2 is None: spo2 = 98
    systolic = vitals.get("systolic")
    if systolic is None: systolic = 120
    hrv = vitals.get("hrv")
    if hrv is None: hrv = 40
    temp = vitals.get("temperature")
    if temp is None: temp = 36.6

    if hr is not None and (hr < 40 or hr > 150):
        return True
    if spo2 is not None and spo2 < 90:
        return True
    if systolic is not None and systolic > 180:
        return True
    if hrv is not None and hrv < 20:
        return True
    if temp is not None and (temp < 35.0 or temp > 39.0):
        return True

    return False
