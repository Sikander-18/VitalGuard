import { useState, useEffect } from "react";

export interface RealTimeVitals {
  heartRate: number | string;
  spo2: number | string;
  bloodPressure: string;
  hrv: number | string;
  timestamp: string;
}

export interface AIClassification {
  condition: string;   // 'normal' | 'future_alert' | 'critical'
  severity: string;    // 'low' | 'medium' | 'high'
  reasoning: string;
  actions: string[];
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
    timestamp: new Date().toISOString(),
  });
  const [history, setHistory] = useState<RealTimeVitals[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [backendConnected, setBackendConnected] = useState(false);
  const [aiClassification, setAiClassification] = useState<AIClassification | null>(null);
  const [locationStatus, setLocationStatus] = useState<LocationStatus>("PROMPT");
  const [coords, setCoords] = useState<{ lat: number; lng: number } | null>(null);

  // Load history from Backend (primary) and localStorage (fallback)
  useEffect(() => {
    const fetchHistory = async () => {
      try {
        const response = await fetch(`http://localhost:8000/vitals/${userId}`);
        if (response.ok) {
          const data = await response.json();
          const mapped: RealTimeVitals[] = data.map((v: any) => ({
            heartRate: v.bpm || "--",
            spo2: v.spo2 || "--",
            bloodPressure: (v.systolic && v.diastolic) ? `${v.systolic}/${v.diastolic}` : "--/--",
            hrv: v.hrv || "--",
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

  // Polling logic (Relay Data)
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
        console.error("Relay polling error:", err);
        setIsConnected(false);
      }
    };

    const interval = setInterval(fetchVitals, 3000);
    fetchVitals();

    return () => clearInterval(interval);
  }, []);

  // Location Tracking logic
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
          userId, // Dynamic user ID
          timestamp: new Date().toISOString()
        }));
      },
      (error) => {
        console.error("Location error:", error);
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

  // WebSocket connection to FastAPI for AI-classified vitals
  useEffect(() => {
    if (!userId) return;

    let ws: WebSocket | null = null;
    let reconnectTimer: ReturnType<typeof setTimeout>;

    const connect = () => {
      try {
        ws = new WebSocket(`ws://localhost:8000/ws/${userId}`);

        ws.onopen = () => {
          console.log(`🔌 WebSocket connected to FastAPI for user ${userId}`);
          setBackendConnected(true);
        };

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            if (data.condition) {
              setAiClassification({
                condition: data.condition,
                severity: data.severity || "low",
                reasoning: data.reasoning || "",
                actions: data.actions ? JSON.parse(data.actions) : [],
              });
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
          ws?.close();
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
      ws?.close();
    };
  }, [userId]);

  return { currentVitals, history, isConnected, backendConnected, aiClassification, locationStatus, coords };
};
