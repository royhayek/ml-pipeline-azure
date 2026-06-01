interface StatCardProps {
  index: number;
  value: string | number;
  label: string;
  unit?: string;
  accent?: "violet" | "teal" | "default";
  delay?: number;
}

const accentMap = {
  violet: "text-violet-400",
  teal: "text-teal-400",
  default: "text-white",
};

export default function StatCard({ index, value, label, unit, accent = "default", delay = 0 }: StatCardProps) {
  return (
    <div
      className="card card-hover p-6 flex flex-col gap-4 animate-fade-up group relative overflow-hidden"
      style={{ animationDelay: `${delay}ms` }}
    >
      {/* Subtle top glow on hover */}
      <div
        className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-violet-500/40 to-transparent
                      opacity-0 group-hover:opacity-100 transition-opacity duration-300"
      />

      <span className="text-[10px] font-mono text-zinc-600 tracking-widest uppercase">
        {String(index).padStart(2, "0")}
      </span>

      <div className="flex items-end gap-1.5 leading-none">
        <span className={`stat-value ${accentMap[accent]}`}>{value}</span>
        {unit && <span className="text-zinc-600 text-lg font-mono mb-0.5">{unit}</span>}
      </div>

      <span className="text-xs text-zinc-500 font-medium uppercase tracking-widest">{label}</span>
    </div>
  );
}
