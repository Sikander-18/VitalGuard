export type RiskLevel = "NORMAL" | "FUTURE_ALERT" | "CRITICAL";

export interface Vitals {
  heartRate: number;
  spo2: number;
  bloodPressureSys: number;
  bloodPressureDia: number;
  hrv: number;
}

export interface VitalHistory {
  time: string;
  heartRate: number;
  spo2: number;
  bpSys: number;
  bpDia: number;
  hrv: number;
}

export interface User {
  id: string;
  name: string;
  age: number;
  vitals: Vitals;
  risk: RiskLevel;
  lat: number;
  lng: number;
}

export interface Doctor {
  id: string;
  name: string;
  specialization: string;
  availability: "Available" | "Busy" | "Off-duty";
  lat: number;
  lng: number;
}

export interface AlertEvent {
  id: string;
  userId: string;
  timestamp: string;
  type: "risk_change" | "alert_triggered";
  severity: RiskLevel;
  reason: string;
}

const generateHistory = (base: Vitals): VitalHistory[] => {
  const data: VitalHistory[] = [];
  const now = Date.now();
  for (let i = 30; i >= 0; i--) {
    const t = new Date(now - i * 60000);
    data.push({
      time: t.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      heartRate: base.heartRate + Math.round((Math.random() - 0.5) * 10),
      spo2: Math.min(100, base.spo2 + Math.round((Math.random() - 0.5) * 3)),
      bpSys: base.bloodPressureSys + Math.round((Math.random() - 0.5) * 8),
      bpDia: base.bloodPressureDia + Math.round((Math.random() - 0.5) * 6),
      hrv: base.hrv + Math.round((Math.random() - 0.5) * 8),
    });
  }
  return data;
};

export const users: User[] = [
  { id: "U001", name: "Sarah Johnson", age: 34, vitals: { heartRate: 72, spo2: 98, bloodPressureSys: 120, bloodPressureDia: 80, hrv: 55 }, risk: "NORMAL", lat: 28.6139, lng: 77.209 },
  { id: "U002", name: "Mike Chen", age: 58, vitals: { heartRate: 95, spo2: 93, bloodPressureSys: 145, bloodPressureDia: 95, hrv: 32 }, risk: "FUTURE_ALERT", lat: 28.6200, lng: 77.215 },
  { id: "U003", name: "Emily Davis", age: 72, vitals: { heartRate: 110, spo2: 88, bloodPressureSys: 170, bloodPressureDia: 105, hrv: 18 }, risk: "CRITICAL", lat: 28.6100, lng: 77.205 },
  { id: "U004", name: "James Wilson", age: 45, vitals: { heartRate: 68, spo2: 97, bloodPressureSys: 118, bloodPressureDia: 78, hrv: 60 }, risk: "NORMAL", lat: 28.625, lng: 77.220 },
  { id: "U005", name: "Priya Patel", age: 62, vitals: { heartRate: 88, spo2: 94, bloodPressureSys: 138, bloodPressureDia: 90, hrv: 35 }, risk: "FUTURE_ALERT", lat: 28.618, lng: 77.212 },
];

export const doctors: Doctor[] = [
  { id: "D001", name: "Dr. Ananya Sharma", specialization: "Cardiologist", availability: "Available", lat: 28.615, lng: 77.211 },
  { id: "D002", name: "Dr. Rajesh Kumar", specialization: "General Physician", availability: "Available", lat: 28.620, lng: 77.218 },
  { id: "D003", name: "Dr. Lisa Wang", specialization: "Pulmonologist", availability: "Busy", lat: 28.612, lng: 77.207 },
  { id: "D004", name: "Dr. Ahmed Hassan", specialization: "Emergency Medicine", availability: "Off-duty", lat: 28.622, lng: 77.213 },
];

export const alerts: AlertEvent[] = [
  { id: "A001", userId: "U003", timestamp: new Date(Date.now() - 120000).toISOString(), type: "alert_triggered", severity: "CRITICAL", reason: "SpO2 dropped below 90%, Heart rate elevated to 110 BPM" },
  { id: "A002", userId: "U002", timestamp: new Date(Date.now() - 300000).toISOString(), type: "risk_change", severity: "FUTURE_ALERT", reason: "Blood pressure trending upward, HRV declining" },
  { id: "A003", userId: "U003", timestamp: new Date(Date.now() - 600000).toISOString(), type: "risk_change", severity: "FUTURE_ALERT", reason: "SpO2 showing declining trend" },
  { id: "A004", userId: "U005", timestamp: new Date(Date.now() - 900000).toISOString(), type: "risk_change", severity: "FUTURE_ALERT", reason: "Elevated blood pressure detected" },
  { id: "A005", userId: "U001", timestamp: new Date(Date.now() - 1800000).toISOString(), type: "risk_change", severity: "NORMAL", reason: "All vitals returned to normal range" },
];

export const currentUser = users[1]; // FUTURE_ALERT user for demo
export const currentUserHistory = generateHistory(currentUser.vitals);

export const getUserHistory = (user: User) => generateHistory(user.vitals);

export const aiSuggestions: Record<string, { explanation: string; actions: string[] }> = {
  FUTURE_ALERT: {
    explanation: "Your vitals indicate early signs of cardiovascular stress. Blood pressure is trending higher and heart rate variability is below optimal range.",
    actions: [
      "Take prescribed medication if available",
      "Practice deep breathing for 5 minutes",
      "Avoid strenuous physical activity",
      "Stay hydrated — drink water",
      "Contact your doctor if symptoms persist",
    ],
  },
  CRITICAL: {
    explanation: "Critical condition detected. Your SpO2 levels are dangerously low and heart rate is significantly elevated, indicating possible respiratory or cardiac distress.",
    actions: [
      "Sit upright immediately to improve breathing",
      "Call emergency services (108) if alone",
      "Use supplemental oxygen if available",
      "Do NOT exert yourself physically",
      "Emergency alert has been sent to your assigned doctor",
    ],
  },
};
