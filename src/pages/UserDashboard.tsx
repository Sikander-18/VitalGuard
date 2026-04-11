import { useState, useEffect, useCallback } from "react";
import { Heart, Wind, Gauge, Activity, Clock, ShieldCheck, ShieldAlert, MapPin, Navigation, Zap, FlaskConical, Loader2 } from "lucide-react";
import Navbar from "@/components/vitalguard/Navbar";
import VitalCard from "@/components/vitalguard/VitalCard";
import RiskIndicator from "@/components/vitalguard/RiskIndicator";
import GraphChart from "@/components/vitalguard/GraphChart";
import AISuggestions from "@/components/vitalguard/AISuggestions";
import MapComponent from "@/components/vitalguard/MapComponent";
import AlertTimeline from "@/components/vitalguard/AlertTimeline";
import { currentUser, doctors, alerts } from "@/data/mockData";
import { useVitals } from "@/hooks/useVitals";
import { useAuth } from "@/context/AuthContext";

type SimScenario = "normal" | "mild_anomaly" | "critical" | "random";

interface SimResult {
  scenario: string;
  ai_condition: string | null;
  ai_severity: string | null;
  ai_reasoning: string | null;
  ai_actions: string[];
  vitals_injected: Record<string, number>;
  message: string;
}

const UserDashboard = () => {
  const { user: authUser } = useAuth();
  const [userProfile, setUserProfile] = useState<any>(null);
  const { currentVitals, history, isConnected, backendConnected, aiClassification, locationStatus } = useVitals(authUser?.uid);
  
  useEffect(() => {
    const fetchProfile = async () => {
      if (!authUser?.uid) return;
      try {
        const response = await fetch(`http://localhost:8000/users/${authUser.uid}`);
        if (response.ok) {
          const data = await response.json();
          setUserProfile({
            id: data.id,
            name: data.name,
            age: data.age,
            gender: data.gender,
            lat: data.location_lat,
            lng: data.location_lng,
            risk: "NORMAL" // Default starting risk
          });
        }
      } catch (e) {
        console.error("Profile fetch error", e);
      }
    };
    fetchProfile();
  }, [authUser?.uid]);

  const activeUser = userProfile || currentUser;
  const userAlerts = alerts.filter((a) => a.userId === activeUser.id);

  // Derive risk level from AI classification or fallback to profile
  const aiRisk = aiClassification?.condition === "critical" ? "CRITICAL" as const
    : aiClassification?.condition === "future_alert" ? "FUTURE_ALERT" as const
    : aiClassification ? "NORMAL" as const
    : activeUser.risk;

  // Map real-time data to chart format
  const chartData = history.map((h) => ({
    time: new Date(h.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    heartRate: typeof h.heartRate === "number" ? h.heartRate : 0,
    spo2: typeof h.spo2 === "number" ? h.spo2 : 0,
    bpSys: h.bloodPressure !== "--/--" ? parseInt(h.bloodPressure.split("/")[0]) : 0,
    bpDia: h.bloodPressure !== "--/--" ? parseInt(h.bloodPressure.split("/")[1]) : 0,
    hrv: typeof h.hrv === "number" ? h.hrv : 0,
  })).reverse();

  // ── Simulate Data ─────────────────────────────────────────────
  const [simLoading, setSimLoading] = useState<SimScenario | null>(null);
  const [simResult, setSimResult] = useState<SimResult | null>(null);

  const simulateScenario = useCallback(async (scenario: SimScenario) => {
    setSimLoading(scenario);
    setSimResult(null);
    try {
      const res = await fetch(
        `http://localhost:8000/simulate/scenario?scenario=${scenario}&user_id=${activeUser.id}`,
        { method: "POST" }
      );
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data: SimResult = await res.json();
      setSimResult(data);
    } catch (err) {
      console.error("Simulate error:", err);
      setSimResult({
        scenario,
        ai_condition: null,
        ai_severity: null,
        ai_reasoning: "Failed to connect to backend. Is the server running on port 8000?",
        ai_actions: [],
        vitals_injected: {},
        message: "❌ Simulation failed — backend unreachable.",
      });
    } finally {
      setSimLoading(null);
    }
  }, [activeUser.id]);

  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      <main className="container py-6 space-y-6">
        <div className="flex justify-between items-start">
          <div>
            <h1 className="text-2xl font-bold text-foreground">Hello, {(activeUser.name || "User").split(" ")[0]} 👋</h1>
            <p className="text-sm text-muted-foreground mt-1">Here's your real-time health overview</p>
          </div>
          
          <div className="flex flex-col sm:flex-row items-end sm:items-center gap-2">
            <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium border ${
              isConnected ? "bg-green-500/10 text-green-500 border-green-500/20" : "bg-red-500/10 text-red-500 border-red-500/20"
            }`}>
              {isConnected ? <ShieldCheck className="w-3.5 h-3.5" /> : <ShieldAlert className="w-3.5 h-3.5" />}
              {isConnected ? "Device Synced" : "Device Disconnected"}
            </div>

            <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium border ${
              locationStatus === "GRANTED" 
                ? "bg-blue-500/10 text-blue-500 border-blue-500/20" 
                : locationStatus === "DENIED" 
                ? "bg-amber-500/10 text-amber-500 border-amber-500/20"
                : "bg-secondary text-muted-foreground border-border/50"
            }`}>
              {locationStatus === "GRANTED" ? <Navigation className="w-3.5 h-3.5 animate-pulse" /> : <MapPin className="w-3.5 h-3.5" />}
              {locationStatus === "GRANTED" ? "Tracking Active" : locationStatus === "DENIED" ? "Location Denied" : "Initializing tracking..."}
            </div>

            <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium border ${
              backendConnected ? "bg-purple-500/10 text-purple-500 border-purple-500/20" : "bg-secondary text-muted-foreground border-border/50"
            }`}>
              <Zap className="w-3.5 h-3.5" />
              {backendConnected ? "AI Engine Online" : "AI Engine Offline"}
            </div>
          </div>
        </div>

        {/* ── Simulate Data Panel ─────────────────────────────── */}
        <div className="bg-card rounded-xl border border-border/50 shadow-sm p-5">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <FlaskConical className="w-5 h-5 text-primary" />
              <h3 className="text-sm font-semibold text-foreground">Simulate Data</h3>
            </div>
            <span className="text-[10px] text-muted-foreground bg-secondary px-2 py-0.5 rounded-full">Demo Mode</span>
          </div>
          <p className="text-xs text-muted-foreground mb-4">
            Inject simulated vital signs to trigger the AI agent pipeline and demonstrate autonomous actions (SMS, Call, Email).
          </p>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
            {([
              { key: "normal" as SimScenario, label: "Normal", emoji: "🟢", desc: "Healthy vitals" },
              { key: "mild_anomaly" as SimScenario, label: "Mild Anomaly", emoji: "🟡", desc: "Elevated risk" },
              { key: "critical" as SimScenario, label: "Critical", emoji: "🔴", desc: "Emergency" },
              { key: "random" as SimScenario, label: "Random", emoji: "🎲", desc: "Surprise" },
            ]).map((s) => (
              <button
                key={s.key}
                onClick={() => simulateScenario(s.key)}
                disabled={simLoading !== null}
                className={`relative flex flex-col items-center gap-1.5 p-3 rounded-lg border transition-all duration-200 ${
                  simLoading === s.key
                    ? "bg-primary/10 border-primary/30 scale-95"
                    : "bg-secondary/30 border-border/50 hover:bg-secondary/60 hover:border-primary/20 hover:scale-[1.02]"
                } disabled:opacity-50 disabled:cursor-not-allowed`}
              >
                {simLoading === s.key ? (
                  <Loader2 className="w-5 h-5 animate-spin text-primary" />
                ) : (
                  <span className="text-lg">{s.emoji}</span>
                )}
                <span className="text-xs font-medium">{s.label}</span>
                <span className="text-[9px] text-muted-foreground">{s.desc}</span>
              </button>
            ))}
          </div>

          {/* Simulate Result Feedback */}
          {simResult && (
            <div className={`mt-4 p-4 rounded-lg border text-sm space-y-2 animate-in fade-in slide-in-from-top-2 duration-300 ${
              simResult.ai_condition === "critical"
                ? "bg-red-500/10 border-red-500/30 text-red-300"
                : simResult.ai_condition === "future_alert"
                ? "bg-amber-500/10 border-amber-500/30 text-amber-300"
                : simResult.ai_condition === "normal"
                ? "bg-green-500/10 border-green-500/30 text-green-300"
                : "bg-secondary border-border/50 text-muted-foreground"
            }`}>
              <div className="flex items-center justify-between">
                <span className="font-semibold text-xs uppercase tracking-wide">
                  {simResult.ai_condition === "critical" ? "🚨 Critical Alert"
                    : simResult.ai_condition === "future_alert" ? "⚠️ Future Alert"
                    : simResult.ai_condition === "normal" ? "✅ Normal"
                    : "📊 Result"}
                </span>
                <span className="text-[10px] opacity-70">Severity: {simResult.ai_severity || "--"}</span>
              </div>
              {simResult.ai_reasoning && (
                <p className="text-xs opacity-90">{simResult.ai_reasoning}</p>
              )}
              {simResult.ai_actions && simResult.ai_actions.length > 0 && (
                <div className="pt-1">
                  <span className="text-[10px] font-semibold uppercase tracking-wider opacity-60">AI Actions:</span>
                  <ul className="mt-1 space-y-0.5">
                    {simResult.ai_actions.map((a, i) => (
                      <li key={i} className="text-[11px] opacity-80 flex items-start gap-1">
                        <span className="mt-0.5">→</span> {a}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              <div className="flex gap-3 pt-1 text-[10px] opacity-60">
                {simResult.vitals_injected.bpm && <span>HR: {simResult.vitals_injected.bpm} bpm</span>}
                {simResult.vitals_injected.spo2 && <span>SpO2: {simResult.vitals_injected.spo2}%</span>}
                {simResult.vitals_injected.systolic && <span>BP: {simResult.vitals_injected.systolic}/{simResult.vitals_injected.diastolic}</span>}
                {simResult.vitals_injected.hrv && <span>HRV: {simResult.vitals_injected.hrv}ms</span>}
              </div>
            </div>
          )}
        </div>

        {/* Vital Cards */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <VitalCard 
            icon={<Heart className="w-5 h-5" />} 
            label="Heart Rate" 
            value={currentVitals.heartRate} 
            unit="BPM" 
            trend={isConnected ? "stable" : "stable"} 
          />
          <VitalCard 
            icon={<Wind className="w-5 h-5" />} 
            label="SpO2" 
            value={currentVitals.spo2} 
            unit="%" 
            trend={currentVitals.spo2 !== "--" && Number(currentVitals.spo2) < 95 ? "down" : "stable"} 
          />
          <VitalCard 
            icon={<Gauge className="w-5 h-5" />} 
            label="Blood Pressure" 
            value={currentVitals.bloodPressure} 
            unit="mmHg" 
            trend={currentVitals.bloodPressure !== "--/--" && parseInt(currentVitals.bloodPressure.split("/")[0]) > 140 ? "up" : "stable"} 
          />
          <VitalCard 
            icon={<Activity className="w-5 h-5" />} 
            label="HRV" 
            value={currentVitals.hrv} 
            unit="ms" 
            trend={currentVitals.hrv !== "--" && Number(currentVitals.hrv) < 40 ? "down" : "stable"} 
          />
        </div>

        {/* AI Classification Alert (from backend) */}
        {aiClassification && aiClassification.condition !== "normal" && (
          <div className={`p-4 rounded-xl border ${
            aiClassification.condition === "critical" 
              ? "bg-red-500/10 border-red-500/30 text-red-400" 
              : "bg-amber-500/10 border-amber-500/30 text-amber-400"
          }`}>
            <div className="flex items-center gap-2 mb-1">
              <Zap className="w-4 h-4" />
              <span className="text-sm font-semibold uppercase">
                {aiClassification.condition === "critical" ? "🚨 Critical Alert" : "⚠️ Future Alert"}
              </span>
              <span className="text-xs opacity-70 ml-auto">Severity: {aiClassification.severity}</span>
            </div>
            <p className="text-xs opacity-80">{aiClassification.reasoning}</p>
          </div>
        )}

        {/* Risk Indicator */}
        <RiskIndicator level={aiRisk} />

        {/* AI Suggestions */}
        <AISuggestions risk={aiRisk} aiData={aiClassification} />

        {/* Graph */}
        <div className="space-y-3">
          <h3 className="font-semibold text-foreground flex items-center gap-2">
            <Activity className="w-4 h-4" /> Live Vitals Chart
          </h3>
          <GraphChart data={chartData.length > 0 ? chartData : []} />
        </div>

        {/* Vitals History Block */}
        <div className="bg-card rounded-xl border border-border/50 shadow-sm overflow-hidden">
          <div className="p-6 pb-3">
            <h3 className="text-sm font-medium flex items-center gap-2">
              <Clock className="w-4 h-4 text-primary" />
              Recorded History (Last 100 Readings)
            </h3>
          </div>
          <div className="p-6 pt-0">
            <div className="max-h-[300px] overflow-y-auto space-y-2 pr-2 custom-scrollbar">
              {history.length > 0 ? (
                history.map((reading, i) => (
                  <div key={i} className="flex items-center justify-between p-3 rounded-lg bg-secondary/30 border border-border/50 hover:bg-secondary/50 transition-colors">
                    <div className="flex flex-col">
                      <span className="text-xs font-medium text-primary">
                        {new Date(reading.timestamp).toLocaleTimeString()}
                      </span>
                      <span className="text-[10px] text-muted-foreground">
                        {new Date(reading.timestamp).toLocaleDateString()}
                      </span>
                    </div>
                    <div className="flex gap-4">
                      <div className="flex flex-col items-center">
                        <span className="text-xs font-bold">{reading.heartRate}</span>
                        <span className="text-[8px] uppercase text-muted-foreground">HR</span>
                      </div>
                      <div className="flex flex-col items-center">
                        <span className="text-xs font-bold">{reading.spo2}%</span>
                        <span className="text-[8px] uppercase text-muted-foreground">SpO2</span>
                      </div>
                      <div className="flex flex-col items-center">
                        <span className="text-xs font-bold">{reading.bloodPressure}</span>
                        <span className="text-[8px] uppercase text-muted-foreground">BP</span>
                      </div>
                    </div>
                  </div>
                ))
              ) : (
                <div className="py-8 text-center text-sm text-muted-foreground italic">
                  Waiting for device sync...
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Map */}
        <div>
          <h3 className="font-semibold text-foreground mb-3">Nearby Doctors</h3>
          <MapComponent
            users={[activeUser]}
            doctors={doctors}
            center={[activeUser.lat ?? 28.6139, activeUser.lng ?? 77.209]}
            className="h-[350px]"
          />
        </div>

        {/* Timeline */}
        <AlertTimeline alerts={userAlerts.length ? userAlerts : alerts.slice(0, 3)} />
      </main>
    </div>
  );
};

export default UserDashboard;
