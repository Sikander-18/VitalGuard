import { ChevronDown, ChevronUp, Cpu, ArrowRight } from "lucide-react";
import { useState } from "react";

interface TraceStep {
  step: string;
  output: string;
  rule?: string;
  input_summary?: string;
}

interface AgentTraceProps {
  trace: TraceStep[];
}

const AGENT_LABELS: Record<string, { label: string; color: string; emoji: string }> = {
  vitals_agent: { label: "Vitals Agent", color: "text-cyan-400 border-cyan-500/20 bg-cyan-500/5", emoji: "🩺" },
  prediction_agent: { label: "Prediction Agent", color: "text-blue-400 border-blue-500/20 bg-blue-500/5", emoji: "🔮" },
  risk_agent: { label: "Risk Agent", color: "text-amber-400 border-amber-500/20 bg-amber-500/5", emoji: "⚖️" },
  action_agent: { label: "Action Agent", color: "text-violet-400 border-violet-500/20 bg-violet-500/5", emoji: "⚡" },
  communication_agent: { label: "Communication Agent", color: "text-emerald-400 border-emerald-500/20 bg-emerald-500/5", emoji: "💬" },
  // Legacy
  vitals_analyzer: { label: "Vitals Analyzer", color: "text-cyan-400 border-cyan-500/20 bg-cyan-500/5", emoji: "🩺" },
  anomaly_detector: { label: "Anomaly Detector", color: "text-amber-400 border-amber-500/20 bg-amber-500/5", emoji: "🔍" },
  decision_maker: { label: "Decision Maker", color: "text-violet-400 border-violet-500/20 bg-violet-500/5", emoji: "⚡" },
  action_executor: { label: "Action Executor", color: "text-emerald-400 border-emerald-500/20 bg-emerald-500/5", emoji: "🎯" },
};

const AgentTrace = ({ trace }: AgentTraceProps) => {
  const [expanded, setExpanded] = useState(false);

  if (!trace || trace.length === 0) return null;

  return (
    <div className="rounded-xl border border-border/50 bg-card/80 backdrop-blur-sm overflow-hidden">
      {/* Header — clickable to expand */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between p-4 hover:bg-secondary/30 transition-colors"
      >
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-purple-500/10">
            <Cpu className="w-4 h-4 text-purple-400" />
          </div>
          <h3 className="text-sm font-semibold text-foreground">Agent Pipeline Trace</h3>
          <span className="text-[10px] text-muted-foreground bg-secondary px-2 py-0.5 rounded-full">
            {trace.length} steps
          </span>
        </div>
        {expanded ? (
          <ChevronUp className="w-4 h-4 text-muted-foreground" />
        ) : (
          <ChevronDown className="w-4 h-4 text-muted-foreground" />
        )}
      </button>

      {/* Pipeline visualization */}
      {expanded && (
        <div className="px-4 pb-4 space-y-3">
          {/* Mini pipeline flow */}
          <div className="flex items-center gap-1 flex-wrap px-2 py-2 bg-secondary/20 rounded-lg">
            {trace.map((step, i) => {
              const agent = AGENT_LABELS[step.step] || {
                label: step.step, color: "text-gray-400 border-gray-500/20 bg-gray-500/5", emoji: "🤖"
              };
              return (
                <div key={i} className="flex items-center gap-1">
                  <span className={`text-[9px] px-2 py-0.5 rounded-full border font-medium ${agent.color}`}>
                    {agent.emoji} {agent.label.split(" ")[0]}
                  </span>
                  {i < trace.length - 1 && (
                    <ArrowRight className="w-3 h-3 text-muted-foreground/30" />
                  )}
                </div>
              );
            })}
          </div>

          {/* Detailed steps */}
          <div className="space-y-2">
            {trace.map((step, i) => {
              const agent = AGENT_LABELS[step.step] || {
                label: step.step, color: "text-gray-400 border-gray-500/20 bg-gray-500/5", emoji: "🤖"
              };
              return (
                <div key={i} className={`rounded-lg border p-3 ${agent.color}`}>
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="text-xs font-semibold">
                      {agent.emoji} {agent.label}
                    </span>
                    {step.rule && (
                      <span className="text-[10px] text-muted-foreground bg-gray-800/50 px-2 py-0.5 rounded-full">
                        {step.rule}
                      </span>
                    )}
                  </div>
                  {step.input_summary && (
                    <p className="text-[10px] text-muted-foreground/60 mb-1">
                      Input: {step.input_summary}
                    </p>
                  )}
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    {step.output}
                  </p>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};

export default AgentTrace;
