import { useState, useEffect } from "react";
import { Heart, Wind, Gauge, Activity, Clock, ShieldCheck, ShieldAlert, MapPin, Navigation, Zap } from "lucide-react";
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
