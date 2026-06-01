import { RefreshCw, Sparkles } from "lucide-react";
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
      {Array.from({ length: 7 }).map((_, i) => (
        <td key={i} className="px-4 py-3">
          <div
            className="h-3 rounded bg-white/[0.05] animate-pulse"
            style={{ width: `${50 + i * 10}%` }}
          />
        </td>
      ))}
    </tr>
  );
}

const COLS = ["#", "File", "Timestamp", "Records", "Avg Predicted Temp", "Latency", "Model"];

export default function InferenceTable({ rows, isFetching, onRefresh }: InferenceTableProps) {
  return (
    <div className="card overflow-hidden">
      {/* Table header */}
      <div className="flex items-center justify-between px-5 py-4 border-b border-white/[0.06]">
        <div>
          <h2 className="text-sm font-semibold text-white">Recent batches</h2>
          <p className="text-[11px] text-zinc-600 mt-0.5">
            Last {rows.length} CSV files · auto-refreshes every 30 s
          </p>
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
              {COLS.map((h) => (
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
                <td colSpan={COLS.length} className="px-4 py-16 text-center text-zinc-600 text-xs">
                  No inferences yet - upload a CSV to the{" "}
                  <code className="font-mono bg-white/[0.05] px-1 rounded">input/</code> container
                  to begin.
                </td>
              </tr>
            ) : (
              rows.flatMap((r, i) => {
                const baseRow = (
                  <tr
                    key={`${r.id}-row`}
                    className={`hover:bg-white/[0.02] transition-colors duration-100
                                ${!r.hf_summary ? "border-b border-white/[0.03]" : ""}`}
                    style={{ animationDelay: `${i * 20}ms` }}
                  >
                    <td className="px-4 py-3 font-mono text-zinc-700 align-top">
                      {String(i + 1).padStart(2, "0")}
                    </td>
                    <td className="px-4 py-3 text-white font-medium max-w-[260px] align-top">
                      <span className="block truncate" title={r.blob_name}>
                        {r.blob_name}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-zinc-500 font-mono whitespace-nowrap align-top">
                      {fmtTs(r.timestamp)}
                    </td>
                    <td className="px-4 py-3 align-top">
                      <span className="badge badge-amber">{r.record_count ?? "—"}</span>
                    </td>
                    <td className="px-4 py-3 text-violet-400 font-mono align-top">
                      {r.confidence_score != null
                        ? `${r.confidence_score.toFixed(2)} °C`
                        : "—"}
                    </td>
                    <td
                      className={`px-4 py-3 font-mono align-top ${
                        (r.latency_ms ?? 0) > 2000 ? "text-amber-400" : "text-zinc-400"
                      }`}
                    >
                      {r.latency_ms != null ? `${r.latency_ms.toFixed(0)} ms` : "—"}
                    </td>
                    <td className="px-4 py-3 align-top">
                      <span
                        className={`badge ${
                          r.model_version?.startsWith("2") ? "badge-teal" : "badge-violet"
                        }`}
                      >
                        v{r.model_version}
                      </span>
                    </td>
                  </tr>
                );

                if (!r.hf_summary) return [baseRow];

                const summaryRow = (
                  <tr
                    key={`${r.id}-summary`}
                    className="border-b border-white/[0.03] bg-white/[0.015]"
                  >
                    <td colSpan={COLS.length} className="px-4 pt-1 pb-3">
                      <div className="flex items-start gap-2 text-[11.5px] text-zinc-400 leading-relaxed">
                        <Sparkles className="w-3 h-3 mt-0.5 text-teal-400/70 shrink-0" />
                        <span className="italic">{r.hf_summary}</span>
                      </div>
                    </td>
                  </tr>
                );

                return [baseRow, summaryRow];
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
