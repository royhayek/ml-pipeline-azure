import { RefreshCw } from "lucide-react";
import type { InferenceRecord } from "../types";

interface InferenceTableProps {
  rows: InferenceRecord[];
  isFetching: boolean;
  onRefresh: () => void;
}

function fmtTs(ts: string): string {
  return new Date(ts).toLocaleString([], {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function SkeletonRow() {
  return (
    <tr className="border-b border-white/[0.04]">
      {Array.from({ length: 6 }).map((_, i) => (
        <td key={i} className="px-4 py-3">
          <div className="h-3 rounded bg-white/[0.05] animate-pulse" style={{ width: `${50 + i * 10}%` }} />
        </td>
      ))}
    </tr>
  );
}

export default function InferenceTable({ rows, isFetching, onRefresh }: InferenceTableProps) {
  return (
    <div className="card overflow-hidden">
      {/* Table header */}
      <div className="flex items-center justify-between px-5 py-4 border-b border-white/[0.06]">
        <div>
          <h2 className="text-sm font-semibold text-white">Recent inferences</h2>
          <p className="text-[11px] text-zinc-600 mt-0.5">Last {rows.length} records · auto-refreshes every 30 s</p>
        </div>
        <button
          onClick={onRefresh}
          disabled={isFetching}
          className="flex items-center gap-1.5 text-[11px] font-mono text-zinc-500
                     border border-white/[0.07] px-3 py-1.5 rounded-md
                     hover:text-zinc-200 hover:border-white/20 transition-all
                     disabled:opacity-40 disabled:cursor-not-allowed"
        >
          <RefreshCw className={`w-3 h-3 ${isFetching ? "animate-spin" : ""}`} />
          Refresh
        </button>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-white/[0.06]">
              {["#", "File", "Timestamp", "Records", "Avg Temp", "Latency", "Model"].map((h) => (
                <th
                  key={h}
                  className="px-4 py-3 text-left text-[10px] font-semibold tracking-widest
                               uppercase text-zinc-600 whitespace-nowrap"
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 && isFetching ? (
              Array.from({ length: 5 }).map((_, i) => <SkeletonRow key={i} />)
            ) : rows.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-4 py-16 text-center text-zinc-600 text-xs">
                  No inferences yet — upload a CSV to the{" "}
                  <code className="font-mono bg-white/[0.05] px-1 rounded">input/</code> container to begin.
                </td>
              </tr>
            ) : (
              rows.map((r, i) => (
                <tr
                  key={r.id}
                  className="border-b border-white/[0.03] hover:bg-white/[0.02]
                               transition-colors duration-100"
                  style={{ animationDelay: `${i * 20}ms` }}
                >
                  <td className="px-4 py-3 font-mono text-zinc-700">{String(i + 1).padStart(2, "0")}</td>
                  <td className="px-4 py-3 text-white font-medium max-w-[240px]">
                    <span className="block truncate" title={r.blob_name}>
                      {r.blob_name}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-zinc-500 font-mono whitespace-nowrap">{fmtTs(r.timestamp)}</td>
                  <td className="px-4 py-3">
                    <span className="badge badge-amber">{r.record_count ?? "—"}</span>
                  </td>
                  <td className="px-4 py-3 text-violet-400 font-mono">
                    {r.confidence_score != null ? `${r.confidence_score.toFixed(2)} °C` : "—"}
                  </td>
                  <td
                    className={`px-4 py-3 font-mono ${(r.latency_ms ?? 0) > 2000 ? "text-amber-400" : "text-zinc-400"}`}
                  >
                    {r.latency_ms != null ? `${r.latency_ms.toFixed(0)} ms` : "—"}
                  </td>
                  <td className="px-4 py-3">
                    <span className="badge badge-violet">{r.model_version}</span>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
