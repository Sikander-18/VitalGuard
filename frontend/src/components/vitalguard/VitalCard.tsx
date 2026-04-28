import { useEffect, useState, useRef } from "react";

interface VitalCardProps {
  icon: React.ReactNode;
  label: string;
  value: string | number;
  unit: string;
  trend?: "up" | "down" | "stable";
  status?: "normal" | "warning" | "critical";
}

const VitalCard = ({ icon, label, value, unit, trend = "stable", status }: VitalCardProps) => {
  const [animate, setAnimate] = useState(false);
  const prevValue = useRef(value);

  // Auto-detect status from value
  const autoStatus = status || (() => {
    if (value === "--" || value === "--/--") return "normal";
    const num = typeof value === "string" ? parseFloat(value.split("/")[0]) : value;
    if (isNaN(num)) return "normal";
    
    if (label === "Heart Rate") {
      if (num > 130 || num < 40) return "critical";
      if (num > 110 || num < 50) return "warning";
    }
    if (label === "SpO2") {
      if (num < 88) return "critical";
      if (num < 94) return "warning";
    }
    if (label === "HRV") {
      if (num < 10) return "critical";
      if (num < 20) return "warning";
    }
    if (label === "Temperature") {
      if (num > 39.5 || num < 35) return "critical";
      if (num > 38.5 || num < 36) return "warning";
    }
    return "normal";
  })();

  // Animate on value change
  useEffect(() => {
    if (prevValue.current !== value) {
      setAnimate(true);
      prevValue.current = value;
      const timer = setTimeout(() => setAnimate(false), 600);
      return () => clearTimeout(timer);
    }
  }, [value]);

  const statusColors = {
    normal: {
      border: "border-emerald-500/20",
      bg: "bg-emerald-500/5",
      icon: "text-emerald-400",
      glow: "shadow-emerald-500/10",
      pulse: "bg-emerald-400",
    },
    warning: {
      border: "border-amber-500/30",
      bg: "bg-amber-500/5",
      icon: "text-amber-400",
      glow: "shadow-amber-500/15",
      pulse: "bg-amber-400",
    },
    critical: {
      border: "border-red-500/40",
      bg: "bg-red-500/8",
      icon: "text-red-400",
      glow: "shadow-red-500/20",
      pulse: "bg-red-400",
    },
  };

  const colors = statusColors[autoStatus];

  const trendIcon = trend === "up" ? "↑" : trend === "down" ? "↓" : "→";
  const trendColor = trend === "up" ? "text-red-400" : trend === "down" ? "text-amber-400" : "text-gray-500";

  return (
    <div className={`relative overflow-hidden rounded-xl border ${colors.border} ${colors.bg} p-4 transition-all duration-500 hover:scale-[1.02] shadow-lg ${colors.glow}`}>
      {/* Subtle pulse indicator for critical */}
      {autoStatus === "critical" && (
        <div className="absolute top-2 right-2">
          <span className="relative flex h-2.5 w-2.5">
            <span className={`animate-ping absolute inline-flex h-full w-full rounded-full ${colors.pulse} opacity-75`}></span>
            <span className={`relative inline-flex rounded-full h-2.5 w-2.5 ${colors.pulse}`}></span>
          </span>
        </div>
      )}

      {/* Animated background gradient */}
      <div className={`absolute inset-0 opacity-5 ${autoStatus === "critical" ? "animate-pulse" : ""}`}>
        <div className={`absolute inset-0 bg-gradient-to-br ${
          autoStatus === "critical" ? "from-red-600 to-red-900" :
          autoStatus === "warning" ? "from-amber-600 to-amber-900" :
          "from-emerald-600 to-emerald-900"
        }`} />
      </div>

      <div className="relative z-10">
        <div className="flex items-center justify-between mb-3">
          <div className={`p-2 rounded-lg ${colors.bg} ${colors.icon}`}>
            {icon}
          </div>
          <span className={`text-xs font-medium ${trendColor}`}>{trendIcon}</span>
        </div>

        <div className={`transition-all duration-300 ${animate ? "scale-110" : "scale-100"}`}>
          <p className={`text-2xl font-bold tracking-tight ${
            autoStatus === "critical" ? "text-red-300" :
            autoStatus === "warning" ? "text-amber-300" :
            "text-foreground"
          }`}>
            {value}
          </p>
        </div>

        <div className="flex items-center justify-between mt-1">
          <span className="text-xs text-muted-foreground font-medium">{label}</span>
          <span className="text-[10px] text-muted-foreground/60 uppercase tracking-wider">{unit}</span>
        </div>
      </div>
    </div>
  );
};

export default VitalCard;
