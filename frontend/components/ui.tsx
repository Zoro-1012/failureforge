// Small presentational helpers shared across pages.
import Link from "next/link";

export function Card({
  children,
  className = "",
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={`rounded-lg border border-forge-border bg-forge-panel p-5 ${className}`}
    >
      {children}
    </div>
  );
}

export function Stat({
  label,
  value,
  hint,
}: {
  label: string;
  value: string;
  hint?: string;
}) {
  return (
    <Card>
      <div className="text-sm text-slate-400">{label}</div>
      <div className="mt-1 text-3xl font-semibold text-white">{value}</div>
      {hint ? <div className="mt-1 text-xs text-slate-500">{hint}</div> : null}
    </Card>
  );
}

const SCENARIO_LABELS: Record<string, string> = {
  redis_outage: "Redis Outage",
  database_deadlock: "Database Deadlock",
  memory_leak: "Memory Leak",
  slow_database: "Slow Database",
};

export function scenarioLabel(id: string): string {
  return SCENARIO_LABELS[id] ?? id;
}

export function Badge({
  children,
  tone = "neutral",
}: {
  children: React.ReactNode;
  tone?: "neutral" | "good" | "bad" | "warn";
}) {
  const tones: Record<string, string> = {
    neutral: "bg-forge-border text-slate-300",
    good: "bg-emerald-500/15 text-emerald-300 border border-emerald-500/30",
    bad: "bg-rose-500/15 text-rose-300 border border-rose-500/30",
    warn: "bg-amber-500/15 text-amber-300 border border-amber-500/30",
  };
  return (
    <span
      className={`inline-flex items-center rounded px-2 py-0.5 text-xs font-medium ${tones[tone]}`}
    >
      {children}
    </span>
  );
}

export function SeverityBadge({ severity }: { severity: string }) {
  const tone =
    severity === "ERROR" ? "bad" : severity === "WARNING" ? "warn" : "neutral";
  return <Badge tone={tone}>{severity}</Badge>;
}

export function IncidentLink({ id }: { id: string }) {
  return (
    <Link href={`/incidents/${id}`} className="text-forge-accent hover:underline">
      {id}
    </Link>
  );
}

export function pct(x: number | null | undefined): string {
  if (x === null || x === undefined) return "—";
  return `${Math.round(x * 1000) / 10}%`;
}
