import { useState, useEffect, useCallback, useRef } from "react";

export interface RealTimeVitals {
  heartRate: number | string;
  spo2: number | string;
  bloodPressure: string;
  hrv: number | string;
  temperature: number | string;
  timestamp: string;
}

export interface RiskAssessment {
  score: number;
  level: string; // LOW | MODERATE | HIGH | CRITICAL
  mews_score: number;
  contributing_factors: string[];
  summary: string;
  trend_alert: string | null;
  trend_summary: Record<string, number> | null;
}

export interface AgentDecision {
  vitals_interpretation: string;
  prediction: {
    forecast_risk: string;
    eta_critical: string;
    confidence: number;
    projected_vitals_5min?: Record<string, number>;
    clinical_forecast?: string;
  };
  decided_action: string;
  action_reasoning: string;
  patient_message: string;
  doctor_message: string;
  contributing_factors: string[];
}

export interface AIClassification {
  condition: string;   // 'normal' | 'future_alert' | 'critical'
  severity: string;    // 'low' | 'medium' | 'high'
  reasoning: string;
  actions: string[];
}

export interface TrendData {
  summary: Record<string, number>;
  alert: string | null;
  mews: number;
}

export interface AgentTrace {
  step: string;
  output: string;
  rule?: string;
  input_summary?: string;
}

export type LocationStatus = "GRANTED" | "DENIED" | "PROMPT" | "ERROR";

const HISTORY_KEY = "vitalguard_history";
const SYNCED_LOCATION_KEY = "vitalguard_synced_location";
const MAX_HISTORY = 100;

export const useVitals = (userId: string = "U002") => {
  const [currentVitals, setCurrentVitals] = useState<RealTimeVitals>({
    heartRate: "--",
    spo2: "--",
    bloodPressure: "--/--",
    hrv: "--",
    temperature: "--",
    timestamp: new Date().toISOString(),
  });
  const [history, setHistory] = useState<RealTimeVitals[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [backendConnected, setBackendConnected] = useState(false);
  const [aiClassification, setAiClassification] = useState<AIClassification | null>(null);
  const [riskAssessment, setRiskAssessment] = useState<RiskAssessment | null>(null);
  const [agentDecision, setAgentDecision] = useState<AgentDecision | null>(null);
  const [trendData, setTrendData] = useState<TrendData | null>(null);
  const [agentTrace, setAgentTrace] = useState<AgentTrace[]>([]);
  const [locationStatus, setLocationStatus] = useState<LocationStatus>("PROMPT");
  const [coords, setCoords] = useState<{ lat: number; lng: number } | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  // Load history from Backend (primary) and localStorage (fallback)
  useEffect(() => {
    const fetchHistory = async () => {
      try {
        const response = await fetch(`http://localhost:8000/vitals/${userId}`);
        if (response.ok) {
          const data = await response.json();
          const mapped: RealTimeVitals[] = data.map((v: any) => ({
            heartRate: v.heart_rate || v.bpm || "--",
            spo2: v.spo2 || "--",
            bloodPressure: (v.systolic && v.diastolic) ? `${v.systolic}/${v.diastolic}` : "--/--",
            hrv: v.hrv || "--",
            temperature: v.temperature || "--",
            timestamp: v.timestamp
          }));
          setHistory(mapped);
          return;
        }
      } catch (e) {
        console.error("Failed to fetch backend history", e);
      }

      const savedHistory = localStorage.getItem(HISTORY_KEY);
      if (savedHistory) {
        try {
          setHistory(JSON.parse(savedHistory));
        } catch (e) {
          console.error("Failed to parse history", e);
        }
      }
    };
    
    if (userId) fetchHistory();
  }, [userId]);

  // Polling logic (Relay Data from BLE hardware)
  useEffect(() => {
    const fetchVitals = async () => {
      try {
        const response = await fetch("http://localhost:5000/data");
        if (!response.ok) throw new Error("Relay unavailable");
        
        const data = await response.json();
        const newVitals: RealTimeVitals = {
          heartRate: data.HR,
          spo2: data.SPO2,
          bloodPressure: data.BP,
          hrv: data.HRV,
          temperature: data.TEMP || "--",
          timestamp: new Date().toISOString(),
        };

        setCurrentVitals(newVitals);
        setIsConnected(true);

        setHistory((prev) => {
          const lastReading = prev[0];
          if (lastReading && 
              lastReading.heartRate === newVitals.heartRate && 
              lastReading.spo2 === newVitals.spo2 && 
              lastReading.bloodPressure === newVitals.bloodPressure) {
            return prev;
          }

          const updatedHistory = [newVitals, ...prev].slice(0, MAX_HISTORY);
          localStorage.setItem(HISTORY_KEY, JSON.stringify(updatedHistory));
          return updatedHistory;
        });
      } catch (err) {
        // BLE relay not available — WebSocket provides data instead
        setIsConnected(false);
      }
    };

    const interval = setInterval(fetchVitals, 3000);
    fetchVitals();

    return () => clearInterval(interval);
  }, []);

  // Location Tracking
  useEffect(() => {
    if (!("geolocation" in navigator)) {
      setLocationStatus("ERROR");
      return;
    }

    const watchId = navigator.geolocation.watchPosition(
      (position) => {
        const newCoords = {
          lat: position.coords.latitude,
          lng: position.coords.longitude,
        };
        setCoords(newCoords);
        setLocationStatus("GRANTED");
        
        localStorage.setItem(SYNCED_LOCATION_KEY, JSON.stringify({
          ...newCoords,
          userId,
          timestamp: new Date().toISOString()
        }));
      },
      (error) => {
        if (error.code === error.PERMISSION_DENIED) {
          setLocationStatus("DENIED");
          localStorage.removeItem(SYNCED_LOCATION_KEY);
        } else {
          setLocationStatus("ERROR");
        }
      },
      { enableHighAccuracy: true, timeout: 5000, maximumAge: 0 }
    );

    return () => navigator.geolocation.clearWatch(watchId);
  }, [userId]);

  // WebSocket — Enhanced protocol for VitalGuard v2
  useEffect(() => {
    if (!userId) return;

    let reconnectTimer: ReturnType<typeof setTimeout>;

    const connect = () => {
      try {
        const ws = new WebSocket(`ws://localhost:8000/ws/${userId}`);
        wsRef.current = ws;

        ws.onopen = () => {
          console.log(`WebSocket connected for user ${userId}`);
          setBackendConnected(true);

          // Send location if available
          if (coords) {
            ws.send(JSON.stringify({
              type: "location_update",
              location: coords,
            }));
          }
        };

        ws.onmessage = (event) => {
          try {
            const msg = JSON.parse(event.data);
            const type = msg.type;
            const data = msg.data || msg;

            switch (type) {
              case "vitals":
                const newVitals: RealTimeVitals = {
                  heartRate: data.heart_rate || data.bpm || data.heartRate || "--",
                  spo2: data.spo2 || "--",
                  bloodPressure: (data.systolic && data.diastolic)
                    ? `${data.systolic}/${data.diastolic}`
                    : data.bloodPressure || "--/--",
                  hrv: data.hrv || "--",
                  temperature: data.temperature || "--",
                  timestamp: data.timestamp || new Date().toISOString(),
                };
                setCurrentVitals(newVitals);
                setIsConnected(true);

                setHistory((prev) => {
                  const updated = [newVitals, ...prev].slice(0, MAX_HISTORY);
                  return updated;
                });
                break;

              case "risk":
                setRiskAssessment({
                  score: data.score || 0,
                  level: data.level || "LOW",
                  mews_score: data.mews_score || 0,
                  contributing_factors: data.contributing_factors || [],
                  summary: data.summary || "",
                  trend_alert: data.trend_alert || null,
                  trend_summary: data.trend_summary || null,
                });
                break;

              case "decision":
                // Update agent decision
                setAgentDecision({
                  vitals_interpretation: data.vitals_interpretation || "",
                  prediction: data.prediction || {},
                  decided_action: data.decided_action || "log",
                  action_reasoning: data.action_reasoning || "",
                  patient_message: data.patient_message || "",
                  doctor_message: data.doctor_message || "",
                  contributing_factors: data.contributing_factors || [],
                });

                // Update legacy AI classification
                setAiClassification({
                  condition: data.condition || "normal",
                  severity: data.severity || "low",
                  reasoning: data.reasoning || data.vitals_interpretation || "",
                  actions: (() => {
                    if (!data.actions) return [];
                    if (typeof data.actions !== "string") return data.actions;
                    try { return JSON.parse(data.actions); } catch { return [String(data.actions)]; }
                  })(),
                });
                break;

              case "trend":
                setTrendData({
                  summary: data.summary || {},
                  alert: data.alert || null,
                  mews: data.mews || 0,
                });
                break;

              case "trace":
                if (Array.isArray(data)) {
                  setAgentTrace(data);
                }
                break;

              case "action":
                // Action execution result — could update UI indicator
                break;

              case "system":
                console.log("[System]", data.message || data);
                break;

              case "error":
                console.error("[Error]", data.message || data);
                break;

              default:
                // Legacy: handle messages without type wrapper
                if (data.condition) {
                  let parsedActions: string[] = [];
                  if (data.actions) {
                    try {
                      parsedActions = JSON.parse(data.actions);
                    } catch {
                      parsedActions = [String(data.actions)];
                    }
                  }
                  setAiClassification({
                    condition: data.condition,
                    severity: data.severity || "low",
                    reasoning: data.reasoning || "",
                    actions: parsedActions,
                  });
                }
            }
          } catch (e) {
            console.error("WebSocket parse error:", e);
          }
        };

        ws.onclose = () => {
          setBackendConnected(false);
          reconnectTimer = setTimeout(connect, 5000);
        };

        ws.onerror = () => {
          setBackendConnected(false);
          ws.close();
        };
      } catch (e) {
        console.error("WebSocket connection error:", e);
        setBackendConnected(false);
        reconnectTimer = setTimeout(connect, 5000);
      }
    };

    connect();

    return () => {
      clearTimeout(reconnectTimer);
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [userId]); // Removed coords dependency to avoid reconnecting

  // Send location updates when coords change, without reconnecting WS
  useEffect(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN && coords) {
      wsRef.current.send(JSON.stringify({
        type: "location_update",
        location: coords,
      }));
    }
  }, [coords]);

  // Send mode change
  const setSimMode = useCallback((mode: string) => {
    // This will be picked up by the WS effect
    const ws = document.querySelector("[data-ws]"); // Placeholder — mode sent via WS
  }, []);

  return {
    currentVitals,
    history,
    isConnected,
    backendConnected,
    aiClassification,
    riskAssessment,
    agentDecision,
    trendData,
    agentTrace,
    locationStatus,
    coords,
  };
};
