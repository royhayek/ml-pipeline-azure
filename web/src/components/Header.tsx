import { Activity, AlertCircle } from "lucide-react";

interface HeaderProps {
  lastSync: Date | null;
  isFetching: boolean;
  error: string | null;
}

function fmt(d: Date): string {
  return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

export default function Header({ lastSync, isFetching, error }: HeaderProps) {
  return (
    <header
      className="sticky top-0 z-50 h-14 flex items-center justify-between px-6
                       bg-[#0a0a10]/80 backdrop-blur-md border-b border-white/[0.06]"
    >
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded-lg bg-violet-500/20 flex items-center justify-center">
            <Activity className="w-3.5 h-3.5 text-violet-400" />
          </div>
          <span className="font-semibold text-white text-sm tracking-tight">ML Pipeline</span>
        </div>
        <span className="text-white/10 select-none">/</span>
        <span className="text-xs text-zinc-500 font-medium">Inference Dashboard</span>
      </div>

      <div className="flex items-center gap-3">
        {error ? (
          <div className="flex items-center gap-1.5 text-red-400 text-xs">
            <AlertCircle className="w-3.5 h-3.5" />
            <span>{error}</span>
          </div>
        ) : (
          <div className="flex items-center gap-1.5">
            <span
              className={`w-1.5 h-1.5 rounded-full ${
                isFetching ? "bg-amber-400 animate-pulse" : "bg-emerald-400 animate-pulse-dot"
              }`}
            />
            <span className="text-xs text-zinc-500 font-mono">
              {isFetching ? "syncing…" : lastSync ? `synced ${fmt(lastSync)}` : "connecting…"}
            </span>
          </div>
        )}
      </div>
    </header>
  );
}
