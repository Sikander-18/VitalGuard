import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import type { VitalHistory } from "@/data/mockData";

interface GraphChartProps {
  data: VitalHistory[];
}

const metrics = [
  { key: "heartRate", label: "Heart Rate", color: "hsl(0, 84%, 60%)", unit: "BPM" },
  { key: "spo2", label: "SpO2", color: "hsl(215, 80%, 50%)", unit: "%" },
  { key: "bpSys", label: "BP (Sys)", color: "hsl(142, 71%, 45%)", unit: "mmHg" },
  { key: "hrv", label: "HRV", color: "hsl(45, 93%, 47%)", unit: "ms" },
] as const;

const MiniChart = ({ data, metric }: { data: { time: string; value: number }[]; metric: typeof metrics[number] }) => (
  <div className="bg-card rounded-xl p-3 shadow-sm border border-border/50">
    <p className="text-xs font-semibold text-foreground mb-1">{metric.label} <span className="text-muted-foreground font-normal">({metric.unit})</span></p>
    <div className="h-28">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 4, right: 4, bottom: 0, left: -20 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="hsl(214, 20%, 92%)" />
          <XAxis dataKey="time" tick={{ fontSize: 9 }} stroke="hsl(215, 10%, 50%)" interval={Math.floor(data.length / 4)} />
          <YAxis tick={{ fontSize: 9 }} stroke="hsl(215, 10%, 50%)" />
          <Tooltip
            contentStyle={{ background: "hsl(0,0%,100%)", border: "1px solid hsl(214,20%,92%)", borderRadius: "0.75rem", fontSize: "0.75rem" }}
            formatter={(value: number) => [`${value} ${metric.unit}`, metric.label]}
          />
          <Line type="monotone" dataKey="value" stroke={metric.color} strokeWidth={2} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  </div>
);

const GraphChart = ({ data }: GraphChartProps) => {
  const scatterData = metrics.map((m) => ({
    metric: m,
    points: data.map((d) => ({ time: d.time, value: d[m.key as keyof VitalHistory] as number })),
  }));

  return (
    <div className="bg-card rounded-xl p-5 shadow-sm border border-border/50">
      <h3 className="font-semibold text-foreground mb-3">Vitals History</h3>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {scatterData.map(({ metric, points }) => (
          <MiniChart key={metric.key} data={points} metric={metric} />
        ))}
      </div>
    </div>
  );
};

export default GraphChart;
