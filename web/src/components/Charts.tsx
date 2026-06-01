import { AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";

interface TempPoint {
  label: string;
  value: number;
}
interface LatPoint {
  label: string;
  value: number;
}

/* ── Custom tooltip ────────────────────────────────────────────────────── */
function ChartTooltip({
  active,
  payload,
  label,
  unit,
}: {
  active?: boolean;
  payload?: Array<{ value: number }>;
  label?: string;
  unit: string;
}) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg border border-white/10 bg-surface-raised px-3 py-2 shadow-xl text-xs font-mono">
      <p className="text-zinc-400 mb-1 truncate max-w-[180px]">{label}</p>
      <p className="text-white font-medium">
        {payload[0].value.toFixed(2)} <span className="text-zinc-500">{unit}</span>
      </p>
    </div>
  );
}

/* ── Temperature bar chart ─────────────────────────────────────────────── */
export function TempChart({ points }: { points: TempPoint[] }) {
  return (
    <ResponsiveContainer width="100%" height={210}>
      <BarChart data={points} margin={{ top: 4, right: 4, left: -20, bottom: 0 }} barCategoryGap="35%">
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" vertical={false} />
        <XAxis
          dataKey="label"
          tick={{ fontSize: 10, fill: "#52525b", fontFamily: "Fira Code, monospace" }}
          tickLine={false}
          axisLine={false}
          interval="preserveStartEnd"
        />
        <YAxis
          tick={{ fontSize: 10, fill: "#52525b", fontFamily: "Fira Code, monospace" }}
          tickLine={false}
          axisLine={false}
          tickFormatter={(v) => `${v.toFixed(0)}°`}
        />
        <Tooltip content={<ChartTooltip unit="°C" />} cursor={{ fill: "rgba(255,255,255,0.03)" }} />
        <Bar dataKey="value" fill="url(#barGrad)" radius={[3, 3, 0, 0]} />
        <defs>
          <linearGradient id="barGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#a78bfa" stopOpacity={0.9} />
            <stop offset="100%" stopColor="#7c3aed" stopOpacity={0.4} />
          </linearGradient>
        </defs>
      </BarChart>
    </ResponsiveContainer>
  );
}

/* ── Latency area chart ────────────────────────────────────────────────── */
export function LatencyChart({ points }: { points: LatPoint[] }) {
  return (
    <ResponsiveContainer width="100%" height={210}>
      <AreaChart data={points} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
        <defs>
          <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#2dd4bf" stopOpacity={0.25} />
            <stop offset="100%" stopColor="#2dd4bf" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" vertical={false} />
        <XAxis
          dataKey="label"
          tick={{ fontSize: 10, fill: "#52525b", fontFamily: "Fira Code, monospace" }}
          tickLine={false}
          axisLine={false}
          interval="preserveStartEnd"
        />
        <YAxis
          tick={{ fontSize: 10, fill: "#52525b", fontFamily: "Fira Code, monospace" }}
          tickLine={false}
          axisLine={false}
          tickFormatter={(v) => `${v}ms`}
        />
        <Tooltip content={<ChartTooltip unit="ms" />} />
        <Area
          type="monotone"
          dataKey="value"
          stroke="#2dd4bf"
          strokeWidth={1.5}
          fill="url(#areaGrad)"
          dot={{ r: 3, fill: "#2dd4bf", strokeWidth: 0 }}
          activeDot={{ r: 4, fill: "#2dd4bf", strokeWidth: 1.5, stroke: "#0a0a10" }}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
