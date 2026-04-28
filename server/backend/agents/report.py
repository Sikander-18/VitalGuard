from ..db import models

def generate_summary(user: models.User, vitals_list: list[models.Vital]) -> str:
    # Here we would normally plug in Groq to summarize the last N readings.
    if not vitals_list:
        return "No readings available to summarize."
        
    avg_bpm = sum([v.bpm for v in vitals_list if v.bpm]) / len([v for v in vitals_list if v.bpm]) if any(v.bpm for v in vitals_list) else 0
    avg_spo2 = sum([v.spo2 for v in vitals_list if v.spo2]) / len([v for v in vitals_list if v.spo2]) if any(v.spo2 for v in vitals_list) else 0
    
    return f"Patient {user.name} has averaged {int(avg_bpm)} BPM and {int(avg_spo2)}% SpO2 over the last {len(vitals_list)} readings. Overall condition seems stable."
