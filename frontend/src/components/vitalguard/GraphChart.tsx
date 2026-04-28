import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine, Area, AreaChart } from "recharts";

interface GraphChartProps {
  data: Array<{
    time: string;
    heartRate: number;
    spo2: number;
    bpSys: number;
    bpDia: number;
    hrv: number;
  }>;
}

const GraphChart = ({ data }: GraphChartProps) => {
  if (!data || data.length === 0) {
    return (
      <div className="rounded-xl border border-border/50 bg-card/60 p-8 flex items-center justify-center min-h-[400px]">
        <p className="text-sm text-muted-foreground italic">Waiting for vitals data...</p>
      </div>
    );
  }

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (!active || !payload?.length) return null;
    return (
      <div className="bg-gray-900/95 backdrop-blur-md border border-gray-700/50 rounded-lg p-3 shadow-xl">
        <p className="text-[10px] text-muted-foreground mb-1.5">{label}</p>
        {payload.map((entry: any, i: number) => (
          <div key={i} className="flex items-center gap-2 text-xs">
            <div className="w-2 h-2 rounded-full" style={{ backgroundColor: entry.color }} />
            <span className="text-gray-400">{entry.name}:</span>
            <span className="font-bold text-gray-200">{entry.value?.toFixed?.(1) ?? entry.value}</span>
          </div>
        ))}
      </div>
    );
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      {/* Heart Rate Chart */}
      <div className="rounded-xl border border-border/50 bg-card/60 p-4">
        <h4 className="text-xs font-semibold text-muted-foreground mb-3 uppercase tracking-wider">Heart Rate</h4>
        <ResponsiveContainer width="100%" height={200}>
          <AreaChart data={data}>
            <defs>
              <linearGradient id="hrGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#f43f5e" stopOpacity={0.3} />
                <stop offset="100%" stopColor="#f43f5e" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
            <XAxis dataKey="time" tick={{ fill: '#6b7280', fontSize: 10 }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fill: '#6b7280', fontSize: 10 }} axisLine={false} tickLine={false} domain={['auto', 'auto']} />
            <Tooltip content={<CustomTooltip />} />
            <ReferenceLine y={100} stroke="#ef4444" strokeDasharray="4 4" strokeOpacity={0.3} />
            <ReferenceLine y={60} stroke="#3b82f6" strokeDasharray="4 4" strokeOpacity={0.3} />
            <Area type="monotone" dataKey="heartRate" stroke="#f43f5e" fill="url(#hrGradient)"
              strokeWidth={2} name="HR" dot={false} animationDuration={800} />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* HRV Chart */}
      <div className="rounded-xl border border-border/50 bg-card/60 p-4">
        <h4 className="text-xs font-semibold text-muted-foreground mb-3 uppercase tracking-wider">Heart Rate Variability</h4>
        <ResponsiveContainer width="100%" height={200}>
          <AreaChart data={data}>
            <defs>
              <linearGradient id="hrvGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#8b5cf6" stopOpacity={0.2} />
                <stop offset="100%" stopColor="#8b5cf6" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
            <XAxis dataKey="time" tick={{ fill: '#6b7280', fontSize: 10 }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fill: '#6b7280', fontSize: 10 }} axisLine={false} tickLine={false} domain={['auto', 'auto']} />
            <Tooltip content={<CustomTooltip />} />
            <ReferenceLine y={20} stroke="#ef4444" strokeDasharray="4 4" strokeOpacity={0.3} />
            <Area type="monotone" dataKey="hrv" stroke="#8b5cf6" fill="url(#hrvGradient)"
              strokeWidth={1.5} name="HRV" dot={false} animationDuration={800} />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* SpO2 Chart */}
      <div className="rounded-xl border border-border/50 bg-card/60 p-4">
        <h4 className="text-xs font-semibold text-muted-foreground mb-3 uppercase tracking-wider">Blood Oxygen (SpO2)</h4>
        <ResponsiveContainer width="100%" height={200}>
          <AreaChart data={data}>
            <defs>
              <linearGradient id="spo2Gradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#06b6d4" stopOpacity={0.3} />
                <stop offset="100%" stopColor="#06b6d4" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
            <XAxis dataKey="time" tick={{ fill: '#6b7280', fontSize: 10 }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fill: '#6b7280', fontSize: 10 }} axisLine={false} tickLine={false} domain={[85, 100]} />
            <Tooltip content={<CustomTooltip />} />
            <ReferenceLine y={94} stroke="#ef4444" strokeDasharray="4 4" strokeOpacity={0.5} />
            <Area type="monotone" dataKey="spo2" stroke="#06b6d4" fill="url(#spo2Gradient)"
              strokeWidth={2} name="SpO2" dot={false} animationDuration={800} />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Blood Pressure Chart */}
      <div className="rounded-xl border border-border/50 bg-card/60 p-4">
        <h4 className="text-xs font-semibold text-muted-foreground mb-3 uppercase tracking-wider">Blood Pressure</h4>
        <ResponsiveContainer width="100%" height={200}>
          <AreaChart data={data}>
            <defs>
              <linearGradient id="bpGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#f59e0b" stopOpacity={0.2} />
                <stop offset="100%" stopColor="#f59e0b" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
            <XAxis dataKey="time" tick={{ fill: '#6b7280', fontSize: 10 }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fill: '#6b7280', fontSize: 10 }} axisLine={false} tickLine={false} domain={['auto', 'auto']} />
            <Tooltip content={<CustomTooltip />} />
            <ReferenceLine y={140} stroke="#ef4444" strokeDasharray="4 4" strokeOpacity={0.3} />
            <ReferenceLine y={90} stroke="#3b82f6" strokeDasharray="4 4" strokeOpacity={0.3} />
            <Area type="monotone" dataKey="bpSys" stroke="#f59e0b" fill="url(#bpGradient)"
              strokeWidth={1.5} name="Systolic" dot={false} animationDuration={800} />
            <Line type="monotone" dataKey="bpDia" stroke="#d97706" strokeWidth={1} strokeDasharray="4 2"
              name="Diastolic" dot={false} animationDuration={800} />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

export default GraphChart;
