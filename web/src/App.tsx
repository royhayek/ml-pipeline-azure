import { useInferences } from "./hooks/useInferences";
import Header from "./components/Header";
import StatCard from "./components/StatCard";
import { TempChart, LatencyChart } from "./components/Charts";
import InferenceTable from "./components/InferenceTable";
import { Thermometer, Timer } from "lucide-react";

function SectionHeader({ children }: { children: React.ReactNode }) {
  return (
    <div className="section-header">
      <span className="section-title">{children}</span>
      <span className="section-line" />
    </div>
  );
}

function ChartCard({
  title,
  subtitle,
  badge,
  children,
}: {
  title: string;
  subtitle: string;
  badge: string;
  children: React.ReactNode;
}) {
  return (
    <div className="card card-hover p-5 animate-fade-up">
      <div className="flex items-start justify-between mb-5">
        <div>
          <h3 className="text-sm font-semibold text-white">{title}</h3>
          <p className="text-[11px] text-zinc-600 mt-0.5">{subtitle}</p>
        </div>
        <span
          className="text-[10px] font-mono text-zinc-600 border border-white/[0.06]
                         px-2 py-1 rounded whitespace-nowrap"
        >
          {badge}
        </span>
      </div>
      {children}
    </div>
  );
}

export default function App() {
  const { data, meta, status, error, lastSync, isFetching, refresh } = useInferences();

  const n = data.length;
  const isLoading = status === "loading";

  // Derived metrics
  const totalPredictions = data.reduce((s, r) => s + (r.record_count ?? 0), 0);
  const latencies = data.map((r) => r.latency_ms ?? 0).filter((v) => v > 0);
  const avgLatency = latencies.length
    ? (latencies.reduce((s, v) => s + v, 0) / latencies.length).toFixed(1)
    : "—";
  const p95Latency = latencies.length
    ? [...latencies].sort((a, b) => a - b)[Math.floor(latencies.length * 0.95)].toFixed(0)
    : "—";
  const avgTemp = n
    ? (data.reduce((s, r) => s + (r.confidence_score ?? 0), 0) / n).toFixed(2)
    : "—";

  // A/B testing aware model display
  const modelCounts = data.reduce<Record<string, number>>((acc, r) => {
    acc[r.model_version] = (acc[r.model_version] ?? 0) + 1;
    return acc;
  }, {});
  const modelVersions = Object.keys(modelCounts).sort();
  const modelLabel = modelVersions.length > 1
    ? modelVersions.map((v) => `v${v}`).join(" / ")
    : modelVersions[0]
      ? `v${modelVersions[0]}`
      : "—";
  const modelSubLabel = modelVersions.length > 1
    ? `A/B · ${modelVersions.map((v) => `${Math.round((modelCounts[v] / n) * 100)}%`).join(" / ")}`
    : "Single revision";

  const ordered = [...data].reverse();

  const tempPoints = ordered.map((r, i) => ({
    label: `#${String(i + 1).padStart(2, "0")}`,
    value: r.confidence_score ?? 0,
    file: r.blob_name.split("/").pop()?.replace(".csv", "") ?? r.blob_name,
    date: new Date(r.timestamp).toLocaleString([], {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    }),
  }));
  const latencyPoints = ordered.map((r, i) => ({
    label: `#${String(i + 1).padStart(2, "0")}`,
    value: r.latency_ms ?? 0,
    file: r.blob_name.split("/").pop()?.replace(".csv", "") ?? r.blob_name,
    date: new Date(r.timestamp).toLocaleString([], {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    }),
  }));

  return (
    <div className="min-h-screen">
      <Header lastSync={lastSync} isFetching={isFetching} error={error} />

      <main className="max-w-[1400px] mx-auto px-6 py-8 space-y-8">
        {/* ── Stats ── */}
        <section>
          <SectionHeader>Pipeline overview</SectionHeader>
          <div className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
            <StatCard
              index={1}
              value={isLoading ? "…" : n}
              label="Files processed"
              accent="violet"
              delay={0}
            />
            <StatCard
              index={2}
              value={isLoading ? "…" : totalPredictions.toLocaleString()}
              label="Predictions made"
              accent="violet"
              delay={60}
            />
            <StatCard
              index={3}
              value={isLoading ? "…" : avgLatency}
              unit="ms"
              label={`Avg ML latency · p95 ${p95Latency}ms`}
              accent="teal"
              delay={120}
            />
            <StatCard
              index={4}
              value={isLoading ? "…" : avgTemp}
              unit="°C"
              label="Avg predicted temp"
              delay={180}
            />
            <StatCard
              index={5}
              value={isLoading ? "…" : modelLabel}
              label={modelSubLabel}
              delay={240}
            />
            <StatCard
              index={6}
              value={isLoading || !meta ? "…" : meta.read_latency_ms.toFixed(0)}
              unit="ms"
              label={`DB read · ${meta?.read_region ?? "Cosmos DB"}`}
              accent="teal"
              delay={300}
            />
          </div>
        </section>

        {/* ── Charts ── */}
        <section>
          <SectionHeader>Per-batch telemetry</SectionHeader>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <ChartCard
              title="Predicted Temperature"
              subtitle="Mean apparent temp per batch (hover for file & time)"
              badge={modelVersions.length > 1 ? `A/B · ${modelLabel}` : `model ${modelLabel}`}
            >
              {n > 0
                ? <TempChart points={tempPoints} />
                : <EmptyChart icon={<Thermometer className="w-5 h-5" />} />
              }
            </ChartCard>

            <ChartCard
              title="Inference Latency"
              subtitle="End-to-end ML API call time per batch (ms)"
              badge="alert if p95 > 2 000 ms"
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
          <SectionHeader>Recent batches</SectionHeader>
          <InferenceTable rows={data} isFetching={isFetching} onRefresh={refresh} />
        </section>
      </main>
    </div>
  );
}

function EmptyChart({ icon }: { icon: React.ReactNode }) {
  return (
    <div className="h-[210px] flex flex-col items-center justify-center gap-2
                    text-zinc-700 border border-dashed border-white/[0.05] rounded-lg">
      {icon}
      <span className="text-xs uppercase tracking-widest">No data yet</span>
    </div>
  );
}
