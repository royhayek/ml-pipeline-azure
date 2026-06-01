import {
  AreaChart, Area, BarChart, Bar,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts'

export interface ChartPoint {
  label: string   // HH:MM — used as X-axis tick
  value: number
  file:  string   // filename — shown in tooltip
  date:  string   // "Jan 5" — shown in tooltip
}

// ── Shared custom tooltip ──────────────────────────────────────────────────
function ChartTooltip({
  active, payload, unit, accentColor,
}: {
  active?:      boolean
  payload?:     Array<{ payload: ChartPoint; value: number }>
  unit:         string
  accentColor:  string
}) {
  if (!active || !payload?.length) return null
  const pt = payload[0].payload
  return (
    <div className="rounded-lg border border-white/10 bg-[#18181e] px-3 py-2.5
                    shadow-xl shadow-black/40 text-xs font-mono space-y-1 min-w-[160px]">
      <p className="text-zinc-500 text-[10px] truncate max-w-[200px]">
        {pt.date} · {pt.label}
      </p>
      <p className="text-zinc-400 truncate max-w-[200px]">{pt.file}</p>
      <p style={{ color: accentColor }} className="font-semibold text-sm pt-0.5">
        {payload[0].value.toFixed(2)}
        <span className="text-zinc-600 font-normal ml-1">{unit}</span>
      </p>
    </div>
  )
}

// ── Temperature bar chart ──────────────────────────────────────────────────
export function TempChart({ points }: { points: ChartPoint[] }) {
  return (
    <ResponsiveContainer width="100%" height={210}>
      <BarChart data={points} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}
                barCategoryGap="35%">
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" vertical={false} />
        <XAxis
          dataKey="label"
          tick={{ fontSize: 10, fill: '#52525b', fontFamily: 'Fira Code, monospace' }}
          tickLine={false} axisLine={false}
          interval="preserveStartEnd"
        />
        <YAxis
          tick={{ fontSize: 10, fill: '#52525b', fontFamily: 'Fira Code, monospace' }}
          tickLine={false} axisLine={false}
          tickFormatter={(v: number) => `${v.toFixed(0)}°`}
          domain={['auto', 'auto']}
        />
        <Tooltip
          content={<ChartTooltip unit="°C" accentColor="#a78bfa" />}
          cursor={{ fill: 'rgba(255,255,255,0.03)' }}
        />
        <defs>
          <linearGradient id="barGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%"   stopColor="#a78bfa" stopOpacity={0.9} />
            <stop offset="100%" stopColor="#7c3aed" stopOpacity={0.4} />
          </linearGradient>
        </defs>
        <Bar dataKey="value" fill="url(#barGrad)" radius={[3, 3, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  )
}

// ── Latency area chart ─────────────────────────────────────────────────────
export function LatencyChart({ points }: { points: ChartPoint[] }) {
  return (
    <ResponsiveContainer width="100%" height={210}>
      <AreaChart data={points} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
        <defs>
          <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%"   stopColor="#2dd4bf" stopOpacity={0.25} />
            <stop offset="100%" stopColor="#2dd4bf" stopOpacity={0}    />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" vertical={false} />
        <XAxis
          dataKey="label"
          tick={{ fontSize: 10, fill: '#52525b', fontFamily: 'Fira Code, monospace' }}
          tickLine={false} axisLine={false}
          interval="preserveStartEnd"
        />
        <YAxis
          tick={{ fontSize: 10, fill: '#52525b', fontFamily: 'Fira Code, monospace' }}
          tickLine={false} axisLine={false}
          tickFormatter={(v: number) => `${v}ms`}
          domain={[0, 'auto']}
        />
        <Tooltip content={<ChartTooltip unit="ms" accentColor="#2dd4bf" />} />
        <Area
          type="monotone" dataKey="value"
          stroke="#2dd4bf" strokeWidth={1.5}
          fill="url(#areaGrad)"
          dot={{ r: 3, fill: '#2dd4bf', strokeWidth: 0 }}
          activeDot={{ r: 4, fill: '#2dd4bf', strokeWidth: 1.5, stroke: '#0a0a10' }}
        />
      </AreaChart>
    </ResponsiveContainer>
  )
}
