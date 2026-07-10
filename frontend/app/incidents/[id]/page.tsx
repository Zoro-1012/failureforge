"use client";

import { use, useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { api, IncidentDetail } from "@/lib/api";
import {
  Card,
  Badge,
  SeverityBadge,
  scenarioLabel,
  pct,
} from "@/components/ui";

export default function IncidentView({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const [incident, setIncident] = useState<IncidentDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [diagnosing, setDiagnosing] = useState(false);

  const load = useCallback(async () => {
    try {
      setIncident(await api.incident(id));
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load incident");
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    load();
  }, [load]);

  async function runDiagnosis() {
    setDiagnosing(true);
    setError(null);
    try {
      await api.diagnose(id);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Diagnosis failed");
    } finally {
      setDiagnosing(false);
    }
  }

  if (loading) {
    return <p className="text-slate-400">Loading {id}…</p>;
  }
  if (error && !incident) {
    return (
      <Card className="border-rose-500/40">
        <p className="text-sm text-rose-300">{error}</p>
        <Link href="/" className="mt-2 inline-block text-sm text-forge-accent hover:underline">
          ← Back to dashboard
        </Link>
      </Card>
    );
  }
  if (!incident) return null;

  const truth = incident.ground_truth.ground_truth;
  const diag = incident.diagnosis;
  const correct = diag ? diag.predicted_cause === truth : null;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <Link href="/" className="text-sm text-forge-accent hover:underline">
            ← Dashboard
          </Link>
          <h1 className="mt-1 text-2xl font-semibold text-white">
            {incident.incident_id}
          </h1>
        </div>
        <div className="text-right text-sm text-slate-400">
          <div>Ground truth</div>
          <Badge>{scenarioLabel(truth)}</Badge>
        </div>
      </div>

      {/* Diagnosis + evaluation result */}
      <Card>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="font-semibold text-white">AI diagnosis</h2>
          {diag ? (
            correct ? (
              <Badge tone="good">✓ Correct</Badge>
            ) : (
              <Badge tone="bad">✗ Incorrect</Badge>
            )
          ) : null}
        </div>

        {!diag ? (
          <div className="flex items-center gap-3">
            <p className="text-sm text-slate-400">
              No diagnosis yet for this incident.
            </p>
            <button
              onClick={runDiagnosis}
              disabled={diagnosing}
              className="rounded-md border border-forge-border bg-forge-bg px-3 py-2 text-sm text-slate-200 hover:border-forge-accent hover:text-white disabled:opacity-50"
            >
              {diagnosing ? "Diagnosing…" : "Run AI diagnosis"}
            </button>
          </div>
        ) : (
          <div className="space-y-3">
            <div className="flex flex-wrap items-center gap-x-8 gap-y-2 text-sm">
              <div>
                <span className="text-slate-400">Predicted: </span>
                <span className="font-medium text-white">
                  {scenarioLabel(diag.predicted_cause)}
                </span>
              </div>
              <div>
                <span className="text-slate-400">Confidence: </span>
                <span className="font-medium text-white">{pct(diag.confidence)}</span>
              </div>
              <div>
                <span className="text-slate-400">Model: </span>
                <span className="text-slate-300">{diag.model}</span>
              </div>
            </div>

            {diag.evidence?.length ? (
              <div>
                <div className="text-sm text-slate-400">Evidence</div>
                <ul className="mt-1 list-inside list-disc space-y-1 text-sm text-slate-300">
                  {diag.evidence.map((e, i) => (
                    <li key={i}>{e}</li>
                  ))}
                </ul>
              </div>
            ) : null}

            {diag.recommended_fix ? (
              <div>
                <div className="text-sm text-slate-400">Recommended fix</div>
                <p className="mt-1 text-sm text-slate-300">{diag.recommended_fix}</p>
              </div>
            ) : null}

            <button
              onClick={runDiagnosis}
              disabled={diagnosing}
              className="text-xs text-slate-500 hover:text-slate-300 disabled:opacity-50"
            >
              {diagnosing ? "Re-diagnosing…" : "Re-run diagnosis"}
            </button>
          </div>
        )}
        {error ? <p className="mt-3 text-sm text-rose-300">{error}</p> : null}
      </Card>

      {/* Telemetry summary */}
      {incident.summary ? (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <MiniStat label="Baseline latency" value={fmtMs(incident.summary.avg_baseline_latency_ms)} />
          <MiniStat label="Failure latency" value={fmtMs(incident.summary.avg_failure_latency_ms)} />
          <MiniStat label="Error logs" value={String(incident.summary.error_log_count)} />
          <MiniStat label="Warning logs" value={String(incident.summary.warning_log_count)} />
        </div>
      ) : null}

      {/* Metrics */}
      <section>
        <h2 className="mb-3 font-semibold text-white">
          Metrics <span className="text-sm font-normal text-slate-500">({incident.metrics.length} samples)</span>
        </h2>
        <Card className="overflow-x-auto p-0">
          <table className="w-full text-sm">
            <thead className="border-b border-forge-border text-left text-slate-400">
              <tr>
                <th className="px-4 py-2 font-medium">Phase</th>
                <th className="px-4 py-2 font-medium">Latency (ms)</th>
                <th className="px-4 py-2 font-medium">CPU %</th>
                <th className="px-4 py-2 font-medium">Memory %</th>
                <th className="px-4 py-2 font-medium">OK</th>
              </tr>
            </thead>
            <tbody>
              {incident.metrics.map((m, i) => (
                <tr key={i} className="border-b border-forge-border/40 last:border-0">
                  <td className="px-4 py-2">
                    <Badge tone={m.phase === "failure" ? "warn" : "neutral"}>{m.phase}</Badge>
                  </td>
                  <td className="px-4 py-2 text-slate-300">{m.request_latency ?? "—"}</td>
                  <td className="px-4 py-2 text-slate-300">{m.cpu_percent ?? "—"}</td>
                  <td className="px-4 py-2 text-slate-300">{m.memory_percent ?? "—"}</td>
                  <td className="px-4 py-2">{m.request_ok ? "✓" : "✗"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      </section>

      {/* Logs */}
      <section>
        <h2 className="mb-3 font-semibold text-white">
          Logs <span className="text-sm font-normal text-slate-500">({incident.logs.length} lines)</span>
        </h2>
        <Card className="max-h-[28rem] overflow-y-auto p-0">
          <table className="w-full text-sm">
            <tbody>
              {incident.logs.map((l, i) => (
                <tr key={i} className="border-b border-forge-border/30 last:border-0 align-top">
                  <td className="whitespace-nowrap px-4 py-1.5 text-xs text-slate-500">
                    {l.timestamp?.slice(11, 19)}
                  </td>
                  <td className="px-2 py-1.5"><SeverityBadge severity={l.severity} /></td>
                  <td className="px-4 py-1.5 font-mono text-xs text-slate-300">{l.message}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      </section>
    </div>
  );
}

function MiniStat({ label, value }: { label: string; value: string }) {
  return (
    <Card>
      <div className="text-xs text-slate-400">{label}</div>
      <div className="mt-1 text-xl font-semibold text-white">{value}</div>
    </Card>
  );
}

function fmtMs(x: number | null | undefined): string {
  return x === null || x === undefined ? "—" : `${x} ms`;
}
