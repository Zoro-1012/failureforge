// Thin client for the FailureForge orchestrator API.

export const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export const SCENARIOS = [
  { id: "redis_outage", label: "Redis Outage" },
  { id: "database_deadlock", label: "Database Deadlock" },
  { id: "memory_leak", label: "Memory Leak" },
  { id: "slow_database", label: "Slow Database" },
] as const;

export type ScenarioId = (typeof SCENARIOS)[number]["id"];

export interface IncidentSummary {
  avg_baseline_latency_ms: number | null;
  avg_failure_latency_ms: number | null;
  max_baseline_memory_percent: number | null;
  max_failure_memory_percent: number | null;
  error_log_count: number;
  warning_log_count: number;
}

export interface IncidentMeta {
  incident_id: string;
  scenario: string;
  ground_truth: string;
  started_at?: string;
  log_count: number;
  metric_count: number;
  summary: IncidentSummary | null;
}

export interface LogRow {
  timestamp: string;
  service: string;
  severity: string;
  message: string;
}

export interface MetricRow {
  timestamp: string;
  phase: string;
  cpu_percent: number | null;
  memory_percent: number | null;
  request_latency: number | null;
  request_ok: boolean | null;
}

export interface Diagnosis {
  predicted_cause: string;
  confidence: number;
  evidence: string[];
  recommended_fix: string;
  model: string;
  created_at?: string;
}

export interface IncidentDetail {
  incident_id: string;
  ground_truth: {
    incident_id: string;
    scenario: string;
    ground_truth: string;
    log_count: number;
    metric_count: number;
  };
  summary: IncidentSummary | null;
  logs: LogRow[];
  metrics: MetricRow[];
  diagnosis: Diagnosis | null;
}

export interface ScenarioStats {
  support: number;
  correct: number;
  accuracy: number;
  precision: number;
  recall: number;
  f1: number;
}

export interface Evaluation {
  total_incidents: number;
  evaluated: number;
  undiagnosed: number;
  correct: number;
  overall: {
    accuracy: number;
    macro_precision: number;
    macro_recall: number;
    macro_f1: number;
  };
  per_scenario: Record<string, ScenarioStats>;
  confusion_matrix: Record<string, Record<string, number>>;
}

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    cache: "no-store",
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`${res.status} ${res.statusText}: ${body}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  evaluation: () => req<Evaluation>("/evaluation"),
  incidents: () => req<{ incidents: IncidentMeta[] }>("/incidents"),
  incident: (id: string) => req<IncidentDetail>(`/incidents/${id}`),
  startScenario: (scenario: ScenarioId) =>
    req<IncidentMeta>("/scenario/start", {
      method: "POST",
      body: JSON.stringify({ scenario }),
    }),
  diagnose: (id: string) =>
    req<Diagnosis>(`/diagnose/${id}`, { method: "POST" }),
};
