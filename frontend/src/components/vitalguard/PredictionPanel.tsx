import { TrendingUp, TrendingDown, Minus, Timer, BarChart3 } from "lucide-react";

interface PredictionPanelProps {
  prediction?: {
    forecast_risk: string;
    eta_critical: string;
    confidence: number;
    projected_vitals_5min?: Record<string, number>;
    clinical_forecast?: string;
  } | null;
  trendData?: {
    summary: Record<string, number>;
    alert: string | null;
    mews: number;
  } | null;
}

const PredictionPanel = ({ prediction, trendData }: PredictionPanelProps) => {
  if (!prediction && !trendData) return null;

  const trends = trendData?.summary || {};
  const hrSlope = trends.hr_slope || 0;
  const spo2Slope = trends.spo2_slope || 0;
  const tempSlope = trends.temp_slope || 0;
  const hrvSlope = trends.hrv_slope || 0;

  const getTrendIcon = (slope: number, inverted: boolean = false) => {
    const isUp = inverted ? slope < -0.01 : slope > 0.01;
    const isDown = inverted ? slope > 0.01 : slope < -0.01;
    if (isUp) return <TrendingUp className="w-3.5 h-3.5 text-red-400" />;
    if (isDown) return <TrendingDown className="w-3.5 h-3.5 text-emerald-400" />;
    return <Minus className="w-3.5 h-3.5 text-gray-500" />;
  };

  const riskColor: Record<string, string> = {
    LOW: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20",
    MODERATE: "text-amber-400 bg-amber-500/10 border-amber-500/20",
    HIGH: "text-orange-400 bg-orange-500/10 border-orange-500/20",
    CRITICAL: "text-red-400 bg-red-500/10 border-red-500/30",
  };

  const forecastRisk = prediction?.forecast_risk || "LOW";

  return (
    <div className="rounded-xl border border-border/50 bg-card/80 backdrop-blur-sm p-5 space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="p-2 rounded-lg bg-blue-500/10">
            <BarChart3 className="w-4 h-4 text-blue-400" />
          </div>
          <h3 className="text-sm font-semibold text-foreground">Predictive Analytics</h3>
        </div>
        {prediction && (
          <span className={`text-[10px] px-2.5 py-1 rounded-full border font-medium ${riskColor[forecastRisk] || riskColor.LOW}`}>
            Forecast: {forecastRisk}
          </span>
        )}
      </div>

      {/* Trend Arrows */}
      <div className="grid grid-cols-4 gap-3">
        {[
          { label: "HR", slope: hrSlope, unit: "bpm/r", icon: getTrendIcon(hrSlope) },
          { label: "SpO2", slope: spo2Slope, unit: "%/r", icon: getTrendIcon(spo2Slope, true) },
          { label: "Temp", slope: tempSlope, unit: "°C/r", icon: getTrendIcon(tempSlope) },
          { label: "HRV", slope: hrvSlope, unit: "ms/r", icon: getTrendIcon(hrvSlope, true) },
        ].map((t) => (
          <div key={t.label} className="flex flex-col items-center p-2.5 rounded-lg bg-secondary/30 border border-border/30">
            {t.icon}
            <span className="text-[10px] font-bold text-foreground/80 mt-1">{t.label}</span>
            <span className="text-[9px] text-muted-foreground">
              {t.slope > 0 ? "+" : ""}{t.slope.toFixed(2)}
            </span>
          </div>
        ))}
      </div>

      {/* Trend Alert */}
      {trendData?.alert && (
        <div className="flex items-start gap-2 p-3 rounded-lg bg-amber-500/5 border border-amber-500/20">
          <Timer className="w-4 h-4 text-amber-400 mt-0.5 flex-shrink-0" />
          <p className="text-xs text-amber-300">{trendData.alert}</p>
        </div>
      )}

      {/* Projected Vitals */}
      {prediction?.projected_vitals_5min && (
        <div className="space-y-1.5">
          <span className="text-[10px] uppercase tracking-wider text-muted-foreground/60 font-semibold">
            Projected (5 min)
          </span>
          <div className="flex gap-3">
            {Object.entries(prediction.projected_vitals_5min).map(([key, val]) => (
              <div key={key} className="flex items-center gap-1.5 text-xs text-muted-foreground">
                <span className="capitalize">{key.replace("_", " ")}:</span>
                <span className="font-bold text-foreground/80">{typeof val === "number" ? val.toFixed(1) : val}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default PredictionPanel;
