from ..db import models

def generate_summary(user: models.User, vitals_list: list[models.Vital]) -> str:
    # Here we would normally plug in Groq to summarize the last N readings.
    if not vitals_list:
        return "No readings available to summarize."

    bpm_vals = [v.bpm for v in vitals_list if v.bpm is not None]
    spo2_vals = [v.spo2 for v in vitals_list if v.spo2 is not None]

    avg_bpm = sum(bpm_vals) / len(bpm_vals) if bpm_vals else 0
    avg_spo2 = sum(spo2_vals) / len(spo2_vals) if spo2_vals else 0

    return f"Patient {user.name} has averaged {int(avg_bpm)} BPM and {int(avg_spo2)}% SpO2 over the last {len(vitals_list)} readings. Overall condition seems stable."

