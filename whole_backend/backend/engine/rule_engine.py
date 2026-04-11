from typing import Dict, Any

def check_vitals_anomaly(vitals: Dict[str, Any]) -> bool:
    """
    Returns True if an anomaly is detected based on basic thresholds, signaling
    that the AI agent should evaluate the reading.
    """
    # bpm
    bpm = vitals.get("bpm")
    if bpm is not None and (bpm < 40 or bpm > 150):
        return True
        
    # SpO2
    spo2 = vitals.get("spo2")
    if spo2 is not None and spo2 < 90:
        return True
        
    # Blood Pressure Systemic
    systolic = vitals.get("systolic")
    if systolic is not None and systolic > 180:
        return True
        
    # HRV
    hrv = vitals.get("hrv")
    if hrv is not None and hrv < 20: # Assuming a sudden drop threshold
        return True
        
    return False
