"use client";

import { useState } from "react";
import { api, SCENARIOS, ScenarioId } from "@/lib/api";
import { Card } from "./ui";

export default function ScenarioRunner({
  onComplete,
}: {
  onComplete?: () => void;
}) {
  const [running, setRunning] = useState<ScenarioId | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [lastIncident, setLastIncident] = useState<string | null>(null);

  async function run(scenario: ScenarioId) {
    setRunning(scenario);
    setError(null);
    try {
      const incident = await api.startScenario(scenario);
      setLastIncident(incident.incident_id);
      onComplete?.();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to run scenario");
    } finally {
      setRunning(null);
    }
  }

  return (
    <Card>
      <div className="mb-3 flex items-center justify-between">
        <h2 className="font-semibold text-white">Run a failure scenario</h2>
        {running ? (
          <span className="text-xs text-slate-400">
            Running… this takes ~10–20s
          </span>
        ) : null}
      </div>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {SCENARIOS.map((s) => (
          <button
            key={s.id}
            onClick={() => run(s.id)}
            disabled={running !== null}
            className="rounded-md border border-forge-border bg-forge-bg px-3 py-3 text-sm font-medium text-slate-200 transition hover:border-forge-accent hover:text-white disabled:cursor-not-allowed disabled:opacity-50"
          >
            {running === s.id ? "Running…" : s.label}
          </button>
        ))}
      </div>
      {lastIncident ? (
        <p className="mt-3 text-sm text-emerald-300">
          Captured {lastIncident}. It now appears in the incident list below.
        </p>
      ) : null}
      {error ? <p className="mt-3 text-sm text-rose-300">{error}</p> : null}
    </Card>
  );
}
