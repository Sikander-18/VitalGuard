import { ShieldCheck, AlertTriangle, AlertOctagon } from "lucide-react";
import type { RiskLevel } from "@/data/mockData";

interface RiskIndicatorProps {
  level: RiskLevel;
}

const config = {
  NORMAL: {
    icon: ShieldCheck,
    label: "Normal",
    message: "All vitals are within healthy range. Keep it up!",
    classes: "status-normal",
    iconColor: "text-status-normal",
    border: "border-status-normal/30",
  },
  FUTURE_ALERT: {
    icon: AlertTriangle,
    label: "Future Alert",
    message: "Your vitals indicate a potential risk. Please take precautions.",
    classes: "status-warning",
    iconColor: "text-status-warning",
    border: "border-status-warning/30",
  },
  CRITICAL: {
    icon: AlertOctagon,
    label: "Critical",
    message: "Critical condition detected. Emergency alert triggered.",
    classes: "status-critical",
    iconColor: "text-status-critical",
    border: "border-status-critical/30",
  },
};

const RiskIndicator = ({ level }: RiskIndicatorProps) => {
  const c = config[level];
  const Icon = c.icon;
  return (
    <div className={`rounded-xl p-5 border ${c.border} ${c.classes} ${level === "CRITICAL" ? "animate-pulse-glow" : ""}`}>
      <div className="flex items-center gap-3">
        <Icon className={`w-6 h-6 ${c.iconColor}`} />
        <div>
          <p className="font-semibold text-sm">{c.label}</p>
          <p className="text-sm opacity-80 mt-0.5">{c.message}</p>
        </div>
      </div>
    </div>
  );
};

export default RiskIndicator;
