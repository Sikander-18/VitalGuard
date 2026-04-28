import { Clock, AlertTriangle, CheckCircle, Phone, Mail, Bell } from "lucide-react";

interface Alert {
  id?: number;
  userId?: string;
  timestamp?: string;
  risk_level?: string;
  risk_score?: number;
  ai_summary?: string;
  decided_action?: string;
  resolved?: boolean;
  condition?: string;
  type?: string;
  message?: string;
  severity?: string;
}

interface AlertTimelineProps {
  alerts: Alert[];
}

const AlertTimeline = ({ alerts }: AlertTimelineProps) => {
  if (!alerts || alerts.length === 0) {
    return (
      <div className="rounded-xl border border-border/50 bg-card/60 p-6">
        <h3 className="text-sm font-semibold text-foreground mb-4 flex items-center gap-2">
          <Clock className="w-4 h-4 text-primary" /> Alert Timeline
        </h3>
        <div className="py-8 text-center text-sm text-muted-foreground italic">
          No alerts recorded yet
        </div>
      </div>
    );
  }

  const getTimelineColor = (alert: Alert) => {
    const level = alert.risk_level || alert.severity || alert.condition;
    if (level === "CRITICAL" || level === "critical" || level === "high") return "red";
    if (level === "HIGH" || level === "MODERATE" || level === "future_alert" || level === "medium") return "amber";
    return "emerald";
  };

  const getActionIcon = (action: string | undefined) => {
    switch (action) {
      case "call_emergency": return <Phone className="w-3 h-3" />;
      case "schedule_doctor": return <Mail className="w-3 h-3" />;
      case "alert_user": return <Bell className="w-3 h-3" />;
      default: return <CheckCircle className="w-3 h-3" />;
    }
  };

  const colorMap = {
    red: {
      dot: "bg-red-400 shadow-red-400/50",
      line: "bg-red-500/20",
      bg: "bg-red-500/5 border-red-500/20",
      text: "text-red-400",
    },
    amber: {
      dot: "bg-amber-400 shadow-amber-400/50",
      line: "bg-amber-500/20",
      bg: "bg-amber-500/5 border-amber-500/20",
      text: "text-amber-400",
    },
    emerald: {
      dot: "bg-emerald-400 shadow-emerald-400/50",
      line: "bg-emerald-500/20",
      bg: "bg-emerald-500/5 border-emerald-500/20",
      text: "text-emerald-400",
    },
  };

  return (
    <div className="rounded-xl border border-border/50 bg-card/60 p-6">
      <h3 className="text-sm font-semibold text-foreground mb-5 flex items-center gap-2">
        <Clock className="w-4 h-4 text-primary" /> Alert Timeline
      </h3>

      <div className="relative max-h-[400px] overflow-y-auto pr-2 custom-scrollbar">
        {/* Vertical line */}
        <div className="absolute left-3 top-0 bottom-0 w-px bg-border/30" />

        <div className="space-y-4">
          {alerts.map((alert, i) => {
            const color = getTimelineColor(alert);
            const colors = colorMap[color];
            const time = alert.timestamp
              ? new Date(alert.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
              : "--:--";
            const date = alert.timestamp
              ? new Date(alert.timestamp).toLocaleDateString()
              : "";

            return (
              <div key={alert.id || i} className="relative flex items-start gap-4 pl-1">
                {/* Timeline dot */}
                <div className={`relative z-10 w-6 h-6 rounded-full flex items-center justify-center ${colors.bg} border`}>
                  <div className={`w-2.5 h-2.5 rounded-full ${colors.dot} shadow-lg`} />
                </div>

                {/* Content */}
                <div className={`flex-1 rounded-lg border p-3 ${colors.bg} transition-all hover:scale-[1.01]`}>
                  <div className="flex items-center justify-between mb-1.5">
                    <div className="flex items-center gap-2">
                      <span className={`text-xs font-bold uppercase ${colors.text}`}>
                        {alert.risk_level || alert.condition || alert.type || "Alert"}
                      </span>
                      {alert.risk_score !== undefined && (
                        <span className="text-[10px] text-muted-foreground">
                          Score: {alert.risk_score}/100
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-1.5">
                      {alert.decided_action && (
                        <span className={`flex items-center gap-1 text-[10px] ${colors.text}`}>
                          {getActionIcon(alert.decided_action)}
                        </span>
                      )}
                      {alert.resolved && (
                        <span className="text-[10px] text-emerald-400 bg-emerald-400/10 px-1.5 py-0.5 rounded-full">
                          Resolved
                        </span>
                      )}
                    </div>
                  </div>

                  <p className="text-xs text-muted-foreground leading-relaxed">
                    {alert.ai_summary || alert.message || "No details available"}
                  </p>

                  <div className="flex items-center gap-2 mt-2 text-[10px] text-muted-foreground/60">
                    <Clock className="w-3 h-3" />
                    <span>{time}</span>
                    <span>•</span>
                    <span>{date}</span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

export default AlertTimeline;
