import { Clock, AlertTriangle, AlertOctagon, ShieldCheck } from "lucide-react";
import type { AlertEvent } from "@/data/mockData";

interface AlertTimelineProps {
  alerts: AlertEvent[];
}

const severityConfig = {
  NORMAL: { icon: ShieldCheck, classes: "status-normal" },
  FUTURE_ALERT: { icon: AlertTriangle, classes: "status-warning" },
  CRITICAL: { icon: AlertOctagon, classes: "status-critical" },
};

const AlertTimeline = ({ alerts }: AlertTimelineProps) => (
  <div className="bg-card rounded-xl p-5 shadow-sm border border-border/50">
    <div className="flex items-center gap-2 mb-4">
      <Clock className="w-5 h-5 text-primary" />
      <h3 className="font-semibold text-foreground">Alert Timeline</h3>
    </div>
    <div className="space-y-3">
      {alerts.map((alert) => {
        const cfg = severityConfig[alert.severity];
        const Icon = cfg.icon;
        const timeAgo = getTimeAgo(alert.timestamp);
        return (
          <div key={alert.id} className="flex items-start gap-3 p-3 rounded-lg bg-secondary/50">
            <div className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 ${cfg.classes}`}>
              <Icon className="w-4 h-4" />
            </div>
            <div className="min-w-0">
              <div className="flex items-center gap-2 mb-0.5">
                <span className="text-xs font-medium text-muted-foreground">{timeAgo}</span>
                <span className="text-xs text-muted-foreground">• {alert.userId}</span>
              </div>
              <p className="text-sm text-foreground">{alert.reason}</p>
            </div>
          </div>
        );
      })}
    </div>
  </div>
);

function getTimeAgo(ts: string) {
  const diff = Date.now() - new Date(ts).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "Just now";
  if (mins < 60) return `${mins}m ago`;
  return `${Math.floor(mins / 60)}h ago`;
}

export default AlertTimeline;
