import { useInferences } from './hooks/useInferences'
import Header from './components/Header'
import StatCard from './components/StatCard'
import { TempChart, LatencyChart } from './components/Charts'
import InferenceTable from './components/InferenceTable'
import { Thermometer, Timer } from 'lucide-react'

function SectionHeader({ children }: { children: React.ReactNode }) {
  return (
    <div className="section-header">
      <span className="section-title">{children}</span>
      <span className="section-line" />
    </div>
  )
}

function ChartCard({
  title, subtitle, badge, children,
}: {
  title:    string
  subtitle: string
  badge:    string
  children: React.ReactNode
}) {
  return (
    <div className="card card-hover p-5 animate-fade-up">
      <div className="flex items-start justify-between mb-5">
        <div>
          <h3 className="text-sm font-semibold text-white">{title}</h3>
          <p className="text-[11px] text-zinc-600 mt-0.5">{subtitle}</p>
        </div>
        <span className="text-[10px] font-mono text-zinc-600 border border-white/[0.06]
                         px-2 py-1 rounded whitespace-nowrap">
          {badge}
        </span>
      </div>
      {children}
    </div>
  )
}

export default function App() {
  const { data, status, error, lastSync, isFetching, refresh } = useInferences()

  const n          = data.length
  const isLoading  = status === 'loading'
  const avgLatency = n ? (data.reduce((s, r) => s + (r.latency_ms ?? 0), 0) / n).toFixed(1) : '—'
  const avgTemp    = n ? (data.reduce((s, r) => s + (r.confidence_score ?? 0), 0) / n).toFixed(2) : '—'
  const modelVer   = data[0]?.model_version ?? '—'

  const ordered = [...data].reverse()

  // Use short timestamp as the X-axis label; include filename for tooltip
  const tempPoints = ordered.map(r => ({
    label:    new Date(r.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    value:    r.confidence_score ?? 0,
    file:     r.blob_name.split('/').pop()?.replace('.csv', '') ?? r.blob_name,
    date:     new Date(r.timestamp).toLocaleDateString([], { month: 'short', day: 'numeric' }),
  }))
  const latencyPoints = ordered.map(r => ({
    label:    new Date(r.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    value:    r.latency_ms ?? 0,
    file:     r.blob_name.split('/').pop()?.replace('.csv', '') ?? r.blob_name,
    date:     new Date(r.timestamp).toLocaleDateString([], { month: 'short', day: 'numeric' }),
  }))

  return (
    <div className="min-h-screen">
      <Header lastSync={lastSync} isFetching={isFetching} error={error} />

      <main className="max-w-[1400px] mx-auto px-6 py-8 space-y-8">

        {/* ── Stats ── */}
        <section>
          <SectionHeader>Overview</SectionHeader>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <StatCard
              index={1}
              value={isLoading ? '…' : n}
              label="Total inferences"
              accent="violet"
              delay={0}
            />
            <StatCard
              index={2}
              value={isLoading ? '…' : avgLatency}
              unit="ms"
              label="Avg latency"
              accent="teal"
              delay={60}
            />
            <StatCard
              index={3}
              value={isLoading ? '…' : avgTemp}
              unit="°C"
              label="Avg apparent temp"
              delay={120}
            />
            <StatCard
              index={4}
              value={isLoading ? '…' : modelVer}
              label="Model version"
              delay={180}
            />
          </div>
        </section>

        {/* ── Charts ── */}
        <section>
          <SectionHeader>Telemetry</SectionHeader>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <ChartCard
              title="Predicted Temperature"
              subtitle="Avg apparent temperature per file (°C)"
              badge={`GBR · model v${modelVer}`}
            >
              {n > 0
                ? <TempChart points={tempPoints} />
                : <EmptyChart icon={<Thermometer className="w-5 h-5" />} />
              }
            </ChartCard>

            <ChartCard
              title="Inference Latency"
              subtitle="End-to-end ML API call time (ms)"
              badge="p95 alert > 2 000 ms"
            >
              {n > 0
                ? <LatencyChart points={latencyPoints} />
                : <EmptyChart icon={<Timer className="w-5 h-5" />} />
              }
            </ChartCard>
          </div>
        </section>

        {/* ── Table ── */}
        <section>
          <SectionHeader>Recent inferences</SectionHeader>
          <InferenceTable rows={data} isFetching={isFetching} onRefresh={refresh} />
        </section>

      </main>
    </div>
  )
}

function EmptyChart({ icon }: { icon: React.ReactNode }) {
  return (
    <div className="h-[210px] flex flex-col items-center justify-center gap-2
                    text-zinc-700 border border-dashed border-white/[0.05] rounded-lg">
      {icon}
      <span className="text-xs uppercase tracking-widest">No data yet</span>
    </div>
  )
}
