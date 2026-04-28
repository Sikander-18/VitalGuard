import { useEffect, useState } from "react";

interface RiskIndicatorProps {
  level: string;
  score?: number;
  mews?: number;
  factors?: string[];
  summary?: string;
}

const RiskIndicator = ({ level, score, mews, factors = [], summary }: RiskIndicatorProps) => {
  const [displayScore, setDisplayScore] = useState(0);
  
  // Animate score counter
  useEffect(() => {
    if (score === undefined) return;
    const target = score;
    const step = Math.ceil(Math.abs(target - displayScore) / 20);
    const timer = setInterval(() => {
      setDisplayScore((prev) => {
        if (Math.abs(prev - target) <= step) {
          clearInterval(timer);
          return target;
        }
        return prev < target ? prev + step : prev - step;
      });
    }, 30);
    return () => clearInterval(timer);
  }, [score]);

  const levelConfig = {
    LOW: {
      color: "text-emerald-400",
      bg: "bg-emerald-500/10",
      border: "border-emerald-500/20",
      ring: "stroke-emerald-400",
      label: "Normal",
      emoji: "✅",
    },
    NORMAL: {
      color: "text-emerald-400",
      bg: "bg-emerald-500/10",
      border: "border-emerald-500/20",
      ring: "stroke-emerald-400",
      label: "Normal",
      emoji: "✅",
    },
    MODERATE: {
      color: "text-amber-400",
      bg: "bg-amber-500/10",
      border: "border-amber-500/20",
      ring: "stroke-amber-400",
      label: "Moderate",
      emoji: "⚠️",
    },
    FUTURE_ALERT: {
      color: "text-amber-400",
      bg: "bg-amber-500/10",
      border: "border-amber-500/20",
      ring: "stroke-amber-400",
      label: "Future Alert",
      emoji: "⚠️",
    },
    HIGH: {
      color: "text-orange-400",
      bg: "bg-orange-500/10",
      border: "border-orange-500/20",
      ring: "stroke-orange-400",
      label: "High Risk",
      emoji: "🔶",
    },
    CRITICAL: {
      color: "text-red-400",
      bg: "bg-red-500/10",
      border: "border-red-500/30",
      ring: "stroke-red-400",
      label: "Critical",
      emoji: "🚨",
    },
  };

  const config = levelConfig[level as keyof typeof levelConfig] || levelConfig.LOW;
  const percentage = score !== undefined ? Math.min(100, Math.max(0, score)) : 0;
  const circumference = 2 * Math.PI * 54;
  const strokeDashoffset = circumference - (percentage / 100) * circumference;

  return (
    <div className={`rounded-xl border ${config.border} ${config.bg} p-6 transition-all duration-500`}>
      <div className="flex flex-col lg:flex-row items-center gap-6">
        {/* Circular Gauge */}
        <div className="relative flex-shrink-0">
          <svg className="w-36 h-36 -rotate-90" viewBox="0 0 120 120">
            {/* Background ring */}
            <circle cx="60" cy="60" r="54" fill="none" stroke="currentColor"
              strokeWidth="8" className="text-gray-800/30" />
            {/* Score ring */}
            <circle cx="60" cy="60" r="54" fill="none"
              strokeWidth="8" strokeLinecap="round"
              className={`${config.ring} transition-all duration-1000 ease-out`}
              style={{
                strokeDasharray: circumference,
                strokeDashoffset: strokeDashoffset,
              }} />
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className={`text-3xl font-bold ${config.color}`}>{displayScore}</span>
            <span className="text-[10px] text-muted-foreground uppercase tracking-wider">/100</span>
          </div>
        </div>

        {/* Info */}
        <div className="flex-1 text-center lg:text-left">
          <div className="flex items-center gap-2 justify-center lg:justify-start mb-2">
            <span className="text-xl">{config.emoji}</span>
            <h3 className={`text-lg font-bold ${config.color}`}>{config.label}</h3>
          </div>

          {mews !== undefined && (
            <div className="flex items-center gap-2 mb-3">
              <span className="text-xs text-muted-foreground">MEWS Score:</span>
              <div className="flex gap-0.5">
                {Array.from({ length: 14 }, (_, i) => (
                  <div
                    key={i}
                    className={`w-2 h-4 rounded-sm transition-all duration-300 ${
                      i < mews
                        ? mews >= 7 ? "bg-red-400" : mews >= 4 ? "bg-amber-400" : "bg-emerald-400"
                        : "bg-gray-700/50"
                    }`}
                  />
                ))}
              </div>
              <span className={`text-xs font-bold ${config.color}`}>{mews}/14</span>
            </div>
          )}

          {summary && (
            <p className="text-xs text-muted-foreground mb-3 leading-relaxed">{summary}</p>
          )}

          {factors.length > 0 && (
            <div className="space-y-1">
              <span className="text-[10px] uppercase tracking-wider text-muted-foreground/60 font-semibold">Contributing Factors</span>
              <div className="flex flex-wrap gap-1.5">
                {factors.slice(0, 4).map((f, i) => (
                  <span
                    key={i}
                    className={`text-[10px] px-2 py-0.5 rounded-full border ${config.border} ${config.bg} ${config.color}`}
                  >
                    {f.split("+")[0].trim()}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default RiskIndicator;
