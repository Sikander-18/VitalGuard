import { Brain, Lightbulb } from "lucide-react";
import type { RiskLevel } from "@/data/mockData";
import { aiSuggestions } from "@/data/mockData";

interface AISuggestionsProps {
  risk: RiskLevel;
  aiData?: {
    reasoning: string;
    actions: string[];
  } | null;
}

const AISuggestions = ({ risk, aiData }: AISuggestionsProps) => {
  if (risk === "NORMAL") return null;
  
  // Use real AI data if available, fallback to mock
  const data = (aiData && aiData.actions && aiData.actions.length > 0) ? {
    explanation: aiData.reasoning,
    actions: aiData.actions
  } : aiSuggestions[risk];

  if (!data) return null;

  return (
    <div className="bg-card rounded-xl p-5 shadow-sm border border-border/50">
      <div className="flex items-center gap-2 mb-3">
        <Brain className="w-5 h-5 text-primary" />
        <h3 className="font-semibold text-foreground">AI Health Insights</h3>
      </div>
      <p className="text-sm text-muted-foreground mb-4">{data.explanation}</p>
      <div className="space-y-2">
        {data.actions.map((a, i) => (
          <div key={i} className="flex items-start gap-2.5 text-sm">
            <Lightbulb className="w-4 h-4 text-status-warning mt-0.5 shrink-0" />
            <span className="text-foreground">{a}</span>
          </div>
        ))}
      </div>
    </div>
  );
};

export default AISuggestions;
