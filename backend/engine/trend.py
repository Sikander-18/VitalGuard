"""
VitalGuard v2 — Per-Patient Vital History & Trend Analysis
Rolling buffer of recent readings with linear regression for trend detection.
Ported from vitalguard/simulator.py VitalHistory class.
"""

import math
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Deque, List

HISTORY_LEN = 60  # max readings to keep per patient


@dataclass
class VitalReading:
    """A single point-in-time vital sign reading."""
    heart_rate: float
    spo2: float
    temperature: float
    hrv: float
    systolic: int = 120
    diastolic: int = 80
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    patient_id: str = "P001"


class VitalHistory:
    """
    Rolling buffer of recent readings with linear trend detection.
    Uses least-squares regression (no numpy needed).
    """

    def __init__(self, maxlen: int = HISTORY_LEN):
        self._buf: Deque[VitalReading] = deque(maxlen=maxlen)

    def push(self, reading: VitalReading):
        self._buf.append(reading)

    @property
    def count(self) -> int:
        return len(self._buf)

    def last_n(self, n: int) -> List[VitalReading]:
        buf = list(self._buf)
        return buf[-n:] if len(buf) >= n else buf

    def trend_summary(self, n: int = 10) -> dict:
        """
        Returns per-vital slope (units/reading) over last n readings.
        Positive = rising, negative = falling.
        """
        readings = self.last_n(n)
        if len(readings) < 3:
            return {
                "hr_slope": 0.0, "spo2_slope": 0.0,
                "temp_slope": 0.0, "hrv_slope": 0.0,
                "sample_count": len(readings),
            }

        xs = list(range(len(readings)))
        n_ = len(readings)
        x_mean = sum(xs) / n_

        def slope(ys):
            y_mean = sum(ys) / n_
            num = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, ys))
            den = sum((x - x_mean) ** 2 for x in xs)
            return num / den if den else 0.0

        return {
            "hr_slope": round(slope([r.heart_rate for r in readings]), 3),
            "spo2_slope": round(slope([r.spo2 for r in readings]), 4),
            "temp_slope": round(slope([r.temperature for r in readings]), 4),
            "hrv_slope": round(slope([r.hrv for r in readings]), 3),
            "sample_count": n_,
            "latest_hr": round(readings[-1].heart_rate, 1),
            "latest_spo2": round(readings[-1].spo2, 1),
            "latest_temp": round(readings[-1].temperature, 1),
            "latest_hrv": round(readings[-1].hrv, 1),
        }

    def predict_crossing(self, vital: str, threshold: float, n: int = 12) -> Optional[int]:
        """
        Returns estimated readings until `vital` crosses `threshold`,
        or None if not trending that way.
        """
        readings = self.last_n(n)
        if len(readings) < 3:
            return None

        vals = {
            "heart_rate": [r.heart_rate for r in readings],
            "spo2": [r.spo2 for r in readings],
            "temperature": [r.temperature for r in readings],
            "hrv": [r.hrv for r in readings],
        }.get(vital, [])

        if not vals:
            return None

        n_ = len(vals)
        xs = list(range(n_))
        x_mean = sum(xs) / n_
        y_mean = sum(vals) / n_
        num = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, vals))
        den = sum((x - x_mean) ** 2 for x in xs)
        if den == 0:
            return None

        slope = num / den
        if abs(slope) < 1e-6:
            return None

        current = vals[-1]
        steps_needed = (threshold - current) / slope
        if steps_needed <= 0:
            return None

        return int(steps_needed)

    def get_baseline(self) -> dict:
        """Calculate baseline from first 10 normal readings."""
        readings = list(self._buf)
        if len(readings) < 5:
            return {}
        sample = readings[:min(10, len(readings))]
        return {
            "baseline_hr": round(sum(r.heart_rate for r in sample) / len(sample), 1),
            "baseline_spo2": round(sum(r.spo2 for r in sample) / len(sample), 1),
            "baseline_temp": round(sum(r.temperature for r in sample) / len(sample), 1),
            "baseline_hrv": round(sum(r.hrv for r in sample) / len(sample), 1),
        }


# ── Per-Patient Registry ──────────────────────────────────────────

_patient_histories: Dict[str, VitalHistory] = {}


def get_patient_history(patient_id: str) -> VitalHistory:
    """Get or create a VitalHistory for a patient."""
    if patient_id not in _patient_histories:
        _patient_histories[patient_id] = VitalHistory()
    return _patient_histories[patient_id]


def push_vital(patient_id: str, reading: VitalReading):
    """Push a reading into the patient's history."""
    history = get_patient_history(patient_id)
    history.push(reading)


def get_trend_summary(patient_id: str, n: int = 10) -> dict:
    """Get trend summary for a patient."""
    history = get_patient_history(patient_id)
    return history.trend_summary(n)
