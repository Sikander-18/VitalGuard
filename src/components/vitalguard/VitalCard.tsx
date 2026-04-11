import { ReactNode } from "react";

interface VitalCardProps {
  icon: ReactNode;
  label: string;
  value: string | number;
  unit: string;
  trend?: "up" | "down" | "stable";
}

const VitalCard = ({ icon, label, value, unit, trend }: VitalCardProps) => (
  <div className="bg-card rounded-xl p-5 shadow-sm border border-border/50 hover:shadow-md transition-shadow">
    <div className="flex items-center gap-3 mb-3">
      <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center text-primary">
        {icon}
      </div>
      <span className="text-sm font-medium text-muted-foreground">{label}</span>
    </div>
    <div className="flex items-baseline gap-1.5">
      <span className="text-3xl font-semibold text-foreground">{value}</span>
      <span className="text-sm text-muted-foreground">{unit}</span>
      {trend && (
        <span className={`ml-auto text-xs font-medium ${trend === "up" ? "text-status-critical" : trend === "down" ? "text-status-normal" : "text-muted-foreground"}`}>
          {trend === "up" ? "↑" : trend === "down" ? "↓" : "→"}
        </span>
      )}
    </div>
  </div>
);

export default VitalCard;
