import { Brain, MessageSquare, Activity } from "lucide-react";

interface AISuggestionsProps {
  risk: string;
  aiData?: {
    condition: string;
    severity: string;
    reasoning: string;
    actions: string[];
  } | null;
  agentDecision?: {
    vitals_interpretation: string;
    prediction: {
      forecast_risk: string;
      clinical_forecast?: string;
      confidence: number;
    };
    decided_action: string;
    action_reasoning: string;
    patient_message: string;
  } | null;
}

const AISuggestions = ({ risk, aiData, agentDecision }: AISuggestionsProps) => {
  const interpretation = agentDecision?.vitals_interpretation || aiData?.reasoning || "";
  const patientMessage = agentDecision?.patient_message || "";
  const action = agentDecision?.decided_action || "log";
  const actions = aiData?.actions || [];
  const prediction = agentDecision?.prediction;

  const actionBadge: Record<string, { label: string; class: string }> = {
    log: { label: "Logged", class: "bg-gray-500/20 text-gray-400 border-gray-500/30" },
    alert_user: { label: "Patient Alerted", class: "bg-amber-500/20 text-amber-400 border-amber-500/30" },
    schedule_doctor: { label: "Doctor Scheduled", class: "bg-blue-500/20 text-blue-400 border-blue-500/30" },
    call_emergency: { label: "Emergency Called", class: "bg-red-500/20 text-red-400 border-red-500/30" },
  };

  const badge = actionBadge[action] || actionBadge.log;

  return (
    <div className="rounded-xl border border-border/50 bg-card/80 backdrop-blur-sm p-5 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="p-2 rounded-lg bg-violet-500/10">
            <Brain className="w-4 h-4 text-violet-400" />
          </div>
          <h3 className="text-sm font-semibold text-foreground">AI Clinical Insight</h3>
        </div>
        <span className={`text-[10px] px-2.5 py-1 rounded-full border font-medium ${badge.class}`}>
          {badge.label}
        </span>
      </div>

      {/* Patient Message */}
      {patientMessage && (
        <div className="flex items-start gap-3 p-3 rounded-lg bg-secondary/30 border border-border/30">
          <MessageSquare className="w-4 h-4 text-emerald-400 mt-0.5 flex-shrink-0" />
          <p className="text-sm text-foreground/90 leading-relaxed">{patientMessage}</p>
        </div>
      )}

      {/* Clinical Interpretation */}
      {interpretation && (
        <div className="space-y-1.5">
          <span className="text-[10px] uppercase tracking-wider text-muted-foreground/60 font-semibold">
            Clinical Analysis
          </span>
          <p className="text-xs text-muted-foreground leading-relaxed">{interpretation}</p>
        </div>
      )}

      {/* Prediction */}
      {prediction && prediction.forecast_risk && (
        <div className="flex items-center gap-3 p-3 rounded-lg bg-blue-500/5 border border-blue-500/20">
          <Activity className="w-4 h-4 text-blue-400 flex-shrink-0" />
          <div className="flex-1">
            <div className="flex items-center justify-between mb-1">
              <span className="text-[10px] uppercase tracking-wider text-blue-400 font-semibold">
                5-15 Min Forecast
              </span>
              <span className="text-[10px] text-muted-foreground">
                Confidence: {(prediction.confidence * 100).toFixed(0)}%
              </span>
            </div>
            <p className="text-xs text-muted-foreground">
              {prediction.clinical_forecast || `Projected: ${prediction.forecast_risk}`}
            </p>
            {/* Confidence bar */}
            <div className="mt-2 h-1.5 bg-gray-700/50 rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-blue-500 to-blue-400 rounded-full transition-all duration-1000"
                style={{ width: `${prediction.confidence * 100}%` }}
              />
            </div>
          </div>
        </div>
      )}

      {/* Recommended Actions */}
      {actions.length > 0 && (
        <div className="space-y-2">
          <span className="text-[10px] uppercase tracking-wider text-muted-foreground/60 font-semibold">
            Recommended Actions
          </span>
          <div className="space-y-1.5">
            {actions.map((a, i) => (
              <div key={i} className="flex items-start gap-2 text-xs text-muted-foreground">
                <span className="text-violet-400 mt-0.5">→</span>
                <span>{a}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default AISuggestions;
