import { useState, useEffect } from "react";
import { Heart, Wind, Gauge, Activity, UserCheck, Menu, X, Stethoscope } from "lucide-react";
import Navbar from "@/components/vitalguard/Navbar";
import UserList from "@/components/vitalguard/UserList";
import DoctorList from "@/components/vitalguard/DoctorList";
import MapComponent from "@/components/vitalguard/MapComponent";
import VitalCard from "@/components/vitalguard/VitalCard";
import RiskIndicator from "@/components/vitalguard/RiskIndicator";
import GraphChart from "@/components/vitalguard/GraphChart";
import AISuggestions from "@/components/vitalguard/AISuggestions";
import AlertTimeline from "@/components/vitalguard/AlertTimeline";
import DoctorAssignModal from "@/components/vitalguard/DoctorAssignModal";
import AddDoctorModal from "@/components/vitalguard/AddDoctorModal";
import { users, doctors as initialDoctors, alerts } from "@/data/mockData";
import type { User, Doctor } from "@/data/mockData";
import { useVitals } from "@/hooks/useVitals";

const AdminDashboard = () => {
  const [selectedUser, setSelectedUser] = useState<User | null>(null);
  const [showAssignModal, setShowAssignModal] = useState(false);
  const [showAddDoctorModal, setShowAddDoctorModal] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [liveUsers, setLiveUsers] = useState<User[]>([]);
  const [doctorsList, setDoctorsList] = useState<Doctor[]>(initialDoctors);
  const [rightPanelTab, setRightPanelTab] = useState<"users" | "doctors">("users");

  // Initial Fetch of Patients
  useEffect(() => {
    const fetchPatients = async () => {
      try {
        const response = await fetch("http://localhost:8000/users/");
        if (response.ok) {
          const data = await response.json();
          const mapped: User[] = data.map((u: any) => ({
            id: u.id,
            name: u.name,
            age: u.age,
            gender: u.gender,
            lat: u.location_lat,
            lng: u.location_lng,
            risk: "NORMAL", // Will be updated by polling
            vitals: { 
               heartRate: 70, 
               spo2: 98, 
               bloodPressureSys: 120, 
               bloodPressureDia: 80, 
               hrv: 50 
            }
          }));
          setLiveUsers(mapped);
          
          // Default selection if none
          if (mapped.length > 0 && !selectedUser) {
            // No auto-select first to avoid confusion with empty vitals
          }
        }
      } catch (e) {
        console.error("Failed to fetch patients", e);
        // Fallback to mock for demo stability if backend fails
        setLiveUsers(users);
      }
    };
    fetchPatients();
  }, []);

  // Use the useVitals hook for the selected user to show real-time detail
  const { currentVitals, history: selectedHistory, aiClassification } = useVitals(selectedUser?.id);

  // Derive risk for selected user from real-time AI classification
  const selectedRisk = aiClassification?.condition === "critical" ? "CRITICAL" as const
    : aiClassification?.condition === "future_alert" ? "FUTURE_ALERT" as const
    : "NORMAL" as const;

  // Derive selected user history for chart
  const formattedHistory = selectedHistory.map((h) => ({
    time: new Date(h.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    heartRate: typeof h.heartRate === "number" ? h.heartRate : 0,
    spo2: typeof h.spo2 === "number" ? h.spo2 : 0,
    bpSys: h.bloodPressure !== "--/--" ? parseInt(h.bloodPressure.split("/")[0]) : 0,
    bpDia: h.bloodPressure !== "--/--" ? parseInt(h.bloodPressure.split("/")[1]) : 0,
    hrv: typeof h.hrv === "number" ? h.hrv : 0,
  })).reverse();

  // Periodic Refetch + Location Sync for Map
  useEffect(() => {
    const fetchPatients = async () => {
      try {
        const response = await fetch("http://localhost:8000/users/");
        if (response.ok) {
          const data = await response.json();
          const syncedLocationData = localStorage.getItem("vitalguard_synced_location");
          let syncedCoords: any = null;
          if (syncedLocationData) {
            try { syncedCoords = JSON.parse(syncedLocationData); } catch (e) {}
          }

          const mapped: User[] = data.map((u: any) => {
            const isSyncedUser = syncedCoords && u.id === syncedCoords.userId;
            return {
              id: u.id,
              name: u.name,
              age: u.age,
              gender: u.gender,
              lat: isSyncedUser ? syncedCoords.lat : u.location_lat,
              lng: isSyncedUser ? syncedCoords.lng : u.location_lng,
              risk: "NORMAL",
              vitals: { heartRate: 70, spo2: 98, bloodPressureSys: 120, bloodPressureDia: 80, hrv: 50 }
            };
          });
          setLiveUsers(mapped);
        }
      } catch (e) {
        console.error("Polling fetch error", e);
      }
    };

    const interval = setInterval(fetchPatients, 10000); // Pulse check every 10s
    return () => clearInterval(interval);
  }, []);

  // selectedHistory is now provided by useVitals (destructured on line 66)
  const selectedAlerts = selectedUser ? alerts.filter((a) => a.userId === selectedUser.id) : [];

  return (
    <div className="min-h-screen bg-background">
      <Navbar />

      {/* Mobile sidebar toggle */}
      <button
        onClick={() => setSidebarOpen(!sidebarOpen)}
        className="lg:hidden fixed bottom-4 right-4 z-50 w-12 h-12 rounded-full bg-primary text-primary-foreground shadow-lg flex items-center justify-center"
      >
        {sidebarOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
      </button>

      <div className="flex relative">
        {/* Left Panel */}
        <aside
          className={`fixed lg:sticky top-14 z-30 h-[calc(100vh-3.5rem)] w-80 bg-card border-r border-border/50 overflow-y-auto p-4 space-y-6 transition-transform lg:translate-x-0 ${
            sidebarOpen ? "translate-x-0" : "-translate-x-full"
          }`}
        >
           <UserList users={liveUsers} selectedId={selectedUser?.id} onSelect={(u) => { setSelectedUser(u); setRightPanelTab("users"); setSidebarOpen(false); }} />
          <div className="border-t border-border/50 pt-4">
            <DoctorList doctors={doctorsList} onAddDoctor={() => setShowAddDoctorModal(true)} />
          </div>
        </aside>

        {/* Main Panel */}
        <main className="flex-1 min-w-0 p-4 lg:p-6 space-y-6">
          {/* Map */}
          <div>
            <h2 className="font-semibold text-foreground mb-3">Live Overview</h2>
            <MapComponent
              users={liveUsers}
              doctors={doctorsList}
              onUserClick={(u) => { setSelectedUser(u); setRightPanelTab("users"); }}
              selectedUserId={selectedUser?.id}
              className="h-[400px]"
            />
          </div>

          {/* Right Panel Toggle */}
          <div className="flex gap-1 p-1 bg-secondary rounded-lg w-fit">
            <button
              onClick={() => setRightPanelTab("users")}
              className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${rightPanelTab === "users" ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:text-foreground"}`}
            >
              User Details
            </button>
            <button
              onClick={() => setRightPanelTab("doctors")}
              className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${rightPanelTab === "doctors" ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:text-foreground"}`}
            >
              Doctor Details
            </button>
          </div>

          {rightPanelTab === "users" ? (
            <>
              {selectedUser ? (
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <h2 className="text-xl font-bold text-foreground">{selectedUser.name}</h2>
                      <p className="text-sm text-muted-foreground">{selectedUser.id} • Age {selectedUser.age}</p>
                    </div>
                    <button
                      onClick={() => setShowAssignModal(true)}
                      className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:opacity-90 transition-opacity"
                    >
                      <UserCheck className="w-4 h-4" />
                      Appoint Doctor
                    </button>
                  </div>
                  <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                    <VitalCard icon={<Heart className="w-5 h-5" />} label="Heart Rate" value={currentVitals.heartRate} unit="BPM" />
                    <VitalCard icon={<Wind className="w-5 h-5" />} label="SpO2" value={currentVitals.spo2} unit="%" />
                    <VitalCard icon={<Gauge className="w-5 h-5" />} label="BP" value={currentVitals.bloodPressure} unit="mmHg" />
                    <VitalCard icon={<Activity className="w-5 h-5" />} label="HRV" value={currentVitals.hrv} unit="ms" />
                  </div>
                  <RiskIndicator level={selectedRisk} />
                  <AISuggestions risk={selectedRisk} aiData={aiClassification} />
                  {formattedHistory && <GraphChart data={formattedHistory} />}
                  <AlertTimeline alerts={selectedAlerts.length ? selectedAlerts : alerts.slice(0, 2)} />
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center py-20 text-muted-foreground">
                  <Activity className="w-12 h-12 mb-4 opacity-30" />
                  <p className="text-sm">Select a patient from the list or map to view details</p>
                </div>
              )}
            </>
          ) : (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-xl font-bold text-foreground">Enrolled Doctors</h2>
                <button
                  onClick={() => setShowAddDoctorModal(true)}
                  className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:opacity-90 transition-opacity"
                >
                  <Stethoscope className="w-4 h-4" />
                  Add Doctor
                </button>
              </div>
              <div className="space-y-2">
                {doctorsList.map((doc) => (
                  <div key={doc.id} className="flex items-center gap-3 p-4 rounded-xl bg-card border border-border/50 shadow-sm">
                    <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
                      <Stethoscope className="w-5 h-5 text-primary" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium text-foreground">{doc.name}</p>
                      <p className="text-xs text-muted-foreground">{doc.specialization}</p>
                    </div>
                    <span className={`text-xs px-2.5 py-1 rounded-md font-medium ${doc.availability === "Available" ? "status-normal" : doc.availability === "Busy" ? "status-warning" : "text-muted-foreground bg-secondary"}`}>
                      {doc.availability}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Critical Alert Panel */}
          <div>
            <h2 className="font-semibold text-foreground mb-3">Critical Alerts</h2>
            <AlertTimeline alerts={alerts} />
          </div>
        </main>
      </div>

      <DoctorAssignModal
        open={showAssignModal}
        onClose={() => setShowAssignModal(false)}
        doctors={doctorsList}
        user={selectedUser}
      />

      <AddDoctorModal
        open={showAddDoctorModal}
        onClose={() => setShowAddDoctorModal(false)}
        onSave={(doc) => setDoctorsList((prev) => [...prev, doc])}
      />
    </div>
  );
};

export default AdminDashboard;
