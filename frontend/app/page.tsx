"use client";

import { useCallback, useEffect, useState } from "react";
import {
  api,
  Evaluation,
  IncidentMeta,
  SCENARIOS,
} from "@/lib/api";
import {
  Card,
  Stat,
  Badge,
  IncidentLink,
  scenarioLabel,
  pct,
} from "@/components/ui";
import ScenarioRunner from "@/components/ScenarioRunner";

export default function Dashboard() {
  const [evaluation, setEvaluation] = useState<Evaluation | null>(null);
  const [incidents, setIncidents] = useState<IncidentMeta[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      const [ev, inc] = await Promise.all([
        api.evaluation(),
        api.incidents(),
      ]);
      setEvaluation(ev);
      setIncidents(inc.incidents);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load data");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold text-white">Dashboard</h1>
        <p className="mt-1 text-sm text-slate-400">
          Simulate failures, run AI root-cause analysis, and benchmark diagnostic
          accuracy against ground truth.
        </p>
      </div>

      {error ? (
        <Card className="border-rose-500/40">
          <p className="text-sm text-rose-300">
            Could not reach the API at{" "}
            <code className="text-rose-200">{process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}</code>
            . Is the stack running (<code>make up</code>)?
          </p>
          <p className="mt-1 text-xs text-slate-500">{error}</p>
        </Card>
      ) : null}

      <section className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <Stat
          label="Total incidents"
          value={loading ? "…" : String(evaluation?.total_incidents ?? incidents.length)}
        />
        <Stat
          label="Overall accuracy"
          value={loading ? "…" : pct(evaluation?.overall.accuracy)}
          hint={evaluation ? `${evaluation.correct}/${evaluation.evaluated} correct` : undefined}
        />
        <Stat
          label="Macro F1"
          value={loading ? "…" : pct(evaluation?.overall.macro_f1)}
        />
        <Stat
          label="Undiagnosed"
          value={loading ? "…" : String(evaluation?.undiagnosed ?? 0)}
        />
      </section>

      <ScenarioRunner onComplete={load} />

      <section>
        <h2 className="mb-3 font-semibold text-white">Accuracy by scenario</h2>
        <Card className="overflow-x-auto p-0">
          <table className="w-full text-sm">
            <thead className="border-b border-forge-border text-left text-slate-400">
              <tr>
                <th className="px-4 py-3 font-medium">Scenario</th>
                <th className="px-4 py-3 font-medium">Support</th>
                <th className="px-4 py-3 font-medium">Accuracy</th>
                <th className="px-4 py-3 font-medium">Precision</th>
                <th className="px-4 py-3 font-medium">Recall</th>
                <th className="px-4 py-3 font-medium">F1</th>
              </tr>
            </thead>
            <tbody>
              {SCENARIOS.map((s) => {
                const row = evaluation?.per_scenario[s.id];
                return (
                  <tr key={s.id} className="border-b border-forge-border/50 last:border-0">
                    <td className="px-4 py-3 text-slate-200">{s.label}</td>
                    <td className="px-4 py-3 text-slate-400">{row?.support ?? 0}</td>
                    <td className="px-4 py-3">
                      <AccuracyCell value={row?.accuracy} support={row?.support ?? 0} />
                    </td>
                    <td className="px-4 py-3 text-slate-300">{row ? pct(row.precision) : "—"}</td>
                    <td className="px-4 py-3 text-slate-300">{row ? pct(row.recall) : "—"}</td>
                    <td className="px-4 py-3 text-slate-300">{row ? pct(row.f1) : "—"}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </Card>
      </section>

      <section>
        <h2 className="mb-3 font-semibold text-white">Incidents</h2>
        <Card className="overflow-x-auto p-0">
          <table className="w-full text-sm">
            <thead className="border-b border-forge-border text-left text-slate-400">
              <tr>
                <th className="px-4 py-3 font-medium">Incident</th>
                <th className="px-4 py-3 font-medium">Ground truth</th>
                <th className="px-4 py-3 font-medium">Errors</th>
                <th className="px-4 py-3 font-medium">Warnings</th>
                <th className="px-4 py-3 font-medium">Δ Latency</th>
              </tr>
            </thead>
            <tbody>
              {incidents.length === 0 && !loading ? (
                <tr>
                  <td colSpan={5} className="px-4 py-6 text-center text-slate-500">
                    No incidents yet. Run a scenario above to capture one.
                  </td>
                </tr>
              ) : null}
              {incidents.map((inc) => (
                <tr key={inc.incident_id} className="border-b border-forge-border/50 last:border-0">
                  <td className="px-4 py-3"><IncidentLink id={inc.incident_id} /></td>
                  <td className="px-4 py-3">
                    <Badge>{scenarioLabel(inc.ground_truth)}</Badge>
                  </td>
                  <td className="px-4 py-3 text-slate-300">{inc.summary?.error_log_count ?? "—"}</td>
                  <td className="px-4 py-3 text-slate-300">{inc.summary?.warning_log_count ?? "—"}</td>
                  <td className="px-4 py-3 text-slate-300">
                    {inc.summary?.avg_baseline_latency_ms != null &&
                    inc.summary?.avg_failure_latency_ms != null
                      ? `${inc.summary.avg_baseline_latency_ms} → ${inc.summary.avg_failure_latency_ms} ms`
                      : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      </section>
    </div>
  );
}

function AccuracyCell({
  value,
  support,
}: {
  value: number | undefined;
  support: number;
}) {
  if (value === undefined || support === 0) {
    return <span className="text-slate-500">—</span>;
  }
  const tone = value >= 0.8 ? "good" : value >= 0.5 ? "warn" : "bad";
  return <Badge tone={tone}>{pct(value)}</Badge>;
}
