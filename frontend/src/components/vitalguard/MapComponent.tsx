import { useEffect, useState } from "react";
import { MapContainer, TileLayer, Marker, Popup, useMap } from "react-leaflet";
import L from "leaflet";
import { MapPin, Navigation, Crosshair } from "lucide-react";
import type { Doctor, RiskLevel, User } from "@/data/mockData";
import "leaflet/dist/leaflet.css";

// Fix Leaflet's default icon issue with Vite/Webpack
import markerIcon2x from "leaflet/dist/images/marker-icon-2x.png";
import markerIcon from "leaflet/dist/images/marker-icon.png";
import markerShadow from "leaflet/dist/images/marker-shadow.png";

// @ts-ignore
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconUrl: markerIcon,
  iconRetinaUrl: markerIcon2x,
  shadowUrl: markerShadow,
});

interface MapComponentProps {
  users?: User[];
  doctors?: Doctor[];
  center?: [number, number];
  onUserClick?: (user: User) => void;
  selectedUserId?: string;
  className?: string;
}

const riskStyles: Record<RiskLevel, string> = {
  NORMAL: "bg-status-normal",
  FUTURE_ALERT: "bg-status-warning",
  CRITICAL: "bg-status-critical",
};

const riskTextStyles: Record<RiskLevel, string> = {
  NORMAL: "text-status-normal",
  FUTURE_ALERT: "text-status-warning",
  CRITICAL: "text-status-critical",
};

// Component to handle auto-centering when props change or geolocation is found
const MapController = ({ center }: { center: [number, number] }) => {
  const map = useMap();
  useEffect(() => {
    map.setView(center, map.getZoom());
  }, [center, map]);
  return null;
};

const MapComponent = ({ users = [], doctors = [], center, onUserClick, selectedUserId, className = "" }: MapComponentProps) => {
  const [mapCenter, setMapCenter] = useState<[number, number]>(center ?? [28.6139, 77.209]);
  const [userLocation, setUserLocation] = useState<[number, number] | null>(null);

  // Live Location Logic
  useEffect(() => {
    if ("geolocation" in navigator) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          const coords: [number, number] = [position.coords.latitude, position.coords.longitude];
          setUserLocation(coords);
          // If no explicit center is provided, center on the user
          if (!center) {
            setMapCenter(coords);
          }
        },
        (error) => {
          console.error("Error getting location:", error);
        }
      );
    }
  }, [center]);

  // Filter out users with invalid coordinates
  const validUsers = users.filter((u) => u.lat != null && u.lng != null && !isNaN(u.lat) && !isNaN(u.lng));

  // Pre-calculate nearest priority for the header overlay
  const priorityPatient = validUsers.length > 0 
    ? [...validUsers].sort((a, b) => {
        const order = { CRITICAL: 0, FUTURE_ALERT: 1, NORMAL: 2 };
        return order[a.risk] - order[b.risk];
      })[0]
    : null;

  // Custom icon for Patients using L.divIcon to keep the pulse effect
  const createPatientIcon = (risk: RiskLevel, isSelected: boolean) => {
    return L.divIcon({
      className: "custom-div-icon",
      html: `
        <div class="flex items-center gap-2 rounded-full border border-background bg-card px-2.5 py-1.5 shadow-md transition-transform hover:scale-105 ${isSelected ? "ring-2 ring-primary/25" : ""}">
          <span class="h-3 w-3 rounded-full ${riskStyles[risk]} ${risk === "CRITICAL" ? "animate-pulse" : ""}"></span>
          <span class="max-w-[110px] truncate text-xs font-medium text-foreground">${isSelected ? "Selected" : ""}</span>
        </div>
      `,
      iconSize: [40, 40],
      iconAnchor: [20, 20],
    });
  };

  // Custom icon for Doctors
  const doctorIcon = L.divIcon({
    className: "doctor-icon",
    html: `
      <div class="flex h-8 w-8 items-center justify-center rounded-full border border-background bg-primary/90 text-primary-foreground shadow-md">
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-map-pin"><path d="M20 10c0 4.993-5.539 10.163-7.392 11.696a1 1 0 0 1-1.216 0C9.539 20.163 4 14.993 4 10a8 8 0 0 1 16 0Z"/><circle cx="12" cy="10" r="3"/></svg>
      </div>
    `,
    iconSize: [32, 32],
    iconAnchor: [16, 16],
  });

  return (
    <div className={`relative rounded-xl overflow-hidden border border-border/50 shadow-sm bg-card ${className}`}>
      <MapContainer 
        center={mapCenter} 
        zoom={13} 
        className="h-full w-full z-0"
        zoomControl={false}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        
        <MapController center={center ?? mapCenter} />

        {/* Current Focus / User Marker */}
        {userLocation && (
          <Marker position={userLocation}>
            <Popup>
              <div className="text-xs font-semibold">You are here</div>
            </Popup>
          </Marker>
        )}

        {/* Patients */}
        {validUsers.map((user) => (
          <Marker 
            key={user.id} 
            position={[user.lat, user.lng]} 
            icon={createPatientIcon(user.risk || "NORMAL", user.id === selectedUserId)}
            eventHandlers={{
              click: () => onUserClick?.(user),
            }}
          >
            <Popup>
              <div className="p-1">
                <p className="font-bold text-sm mb-1">{user.name}</p>
                <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
                  <span className="text-muted-foreground">Heart Rate:</span>
                  <span className="font-medium">{user.vitals?.heartRate ?? "--"} BPM</span>
                  <span className="text-muted-foreground">SpO2:</span>
                  <span className="font-medium text-status-critical">{user.vitals?.spo2 ?? "--"}%</span>
                </div>
              </div>
            </Popup>
          </Marker>
        ))}

        {/* Doctors */}
        {doctors.map((doctor) => (
          <Marker 
            key={doctor.id} 
            position={[doctor.lat, doctor.lng]} 
            icon={doctorIcon}
          >
            <Popup>
              <div className="p-1">
                <p className="font-bold text-sm">{doctor.name}</p>
                <p className="text-xs text-muted-foreground">{doctor.specialization}</p>
                <p className="text-xs mt-1 font-medium">{doctor.availability}</p>
              </div>
            </Popup>
          </Marker>
        ))}
      </MapContainer>

      {/* Floating Overlays (Z-Index UI) */}
      <div className="absolute left-4 top-4 z-10 rounded-xl border border-border/60 bg-card/90 backdrop-blur px-3 py-2 shadow-sm pointer-events-none">
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <Navigation className="h-3.5 w-3.5 text-primary" />
          <span>Real-time monitoring</span>
        </div>
        <p className="mt-1 text-sm font-medium text-foreground">Live Global Tracking</p>
      </div>

      <div className="absolute bottom-4 left-4 right-4 z-10 grid gap-2 rounded-xl border border-border/60 bg-card/90 p-3 shadow-sm backdrop-blur sm:grid-cols-3 pointer-events-none">
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <span className="h-2.5 w-2.5 rounded-full bg-status-critical" />
          Critical patient
        </div>
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <span className="h-2.5 w-2.5 rounded-full bg-status-warning" />
          Future alert
        </div>
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <MapPin className="h-3.5 w-3.5 text-primary" />
          Enrolled doctor
        </div>
      </div>

      {priorityPatient && (
        <div className="absolute right-4 top-4 z-10 rounded-xl border border-border/60 bg-card/90 px-3 py-2 text-right shadow-sm backdrop-blur pointer-events-none">
          <p className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground">Highest priority</p>
          <p className={`mt-1 text-sm font-semibold ${riskTextStyles[priorityPatient.risk]}`}>
            {priorityPatient.name}
          </p>
        </div>
      )}
    </div>
  );
};

export default MapComponent;
