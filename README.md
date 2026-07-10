# FailureForge

**An AI-powered distributed-systems failure simulation and evaluation platform.**

![CI](https://github.com/sneha-510/failureforge/actions/workflows/ci.yml/badge.svg)

FailureForge creates realistic infrastructure failures in a controlled distributed
environment, captures the telemetry generated during each incident, and evaluates
AI-generated root-cause analyses against **known ground truth** — turning "can an
LLM diagnose this outage?" into a measurable benchmark.

Because every failure is injected deliberately, the true root cause is always
known, which is what makes the diagnostic accuracy scoring valid.

---

## Current features

- **Redis outage simulation** — stops the Redis container; surfaces connection
  failures and elevated latency.
- **Database deadlock simulation** — drives competing transactions to trigger a
  real PostgreSQL deadlock.
- **Memory leak simulation** — retained allocations against a bounded container,
  producing rising memory usage and OOM warnings.
- **Slow database simulation** — injects artificial query delays, producing
  latency spikes.
- **Telemetry collection** — structured JSON logs (`timestamp`, `service`,
  `severity`, `message`) and metrics (`cpu_percent`, `memory_percent`,
  `request_latency`) per incident.
- **Incident persistence** — every incident's logs, metrics, and ground truth are
  stored in PostgreSQL and exported as a portable benchmark dataset.
- **Diagnosis engine** — a single-pass pipeline that produces a structured
  root-cause analysis (`predicted_cause`, `confidence`, `evidence`,
  `recommended_fix`) from logs + metrics. Supports a Gemini-backed provider and an
  offline deterministic provider for reproducible runs/CI.
- **Evaluation framework** — accuracy, precision, recall, and F1 (overall and per
  scenario) plus a confusion matrix, comparing predictions to ground truth.
- **Dashboard** — a Next.js UI to launch scenarios, inspect incidents (logs,
  metrics, diagnosis vs. ground truth), and view benchmark metrics.

### Verified with real telemetry

The **simulate → telemetry → persistence** pipeline has been run end-to-end in
Docker and verified with real captured data:

- Redis outages generate `connection refused` errors and latency increases.
- Slow-database scenarios generate clear latency spikes (≈26 ms → ≈1040 ms).
- Memory-leak scenarios generate warning logs and rising memory usage.
- Incidents and their telemetry are persisted and queried back correctly.

The diagnosis and evaluation layers are implemented and covered by unit tests plus
a deterministic end-to-end suite (using the offline diagnosis provider). The
Gemini-backed diagnosis path is implemented and runs when an API key is supplied.

---

## Architecture

```
        User
         │
         ▼
  Next.js Dashboard            (:3000)
         │
         ▼
  FastAPI Backend / Orchestrator   (:8000)
         │
         ▼
  Failure Orchestrator   ── controls containers via the Docker socket
         │
         ▼
  Distributed Environment    ── Application service (:8001) + PostgreSQL + Redis
         │
         ▼
  Telemetry Collection   ── logs + metrics per incident
         │
         ▼
  PostgreSQL             ── incidents · logs · metrics · diagnoses
         │
         ▼
  Diagnosis Engine       ── logs + metrics → root-cause analysis
         │
         ▼
  Evaluation Engine      ── prediction vs. ground truth → accuracy / precision / recall
```

A detailed component diagram, request sequence, and data model (rendered with
Mermaid) are in [`ARCHITECTURE.md`](ARCHITECTURE.md).

### Tech stack

Backend: Python, FastAPI · Frontend: Next.js 15, TypeScript, Tailwind CSS ·
Storage: PostgreSQL · Cache: Redis · AI: Gemini API · Infra: Docker, Docker
Compose · Tests: Pytest, Playwright.

### Repository layout

```
backend/
  app/            Application service (the system under test)
  orchestrator/   Control plane: scenarios, telemetry, storage, diagnosis, evaluation
frontend/         Next.js 15 + TypeScript + Tailwind dashboard
docker/           docker-compose.yml
datasets/         Exported benchmark incidents (incident_NNN/…)
scripts/          Demo + E2E runners
docs/             Per-phase notes, E2E guide
tests/            Pytest (unit + live-stack)
```

---

## Quick start

Requires Docker Desktop (with Docker Compose).

```bash
git clone https://github.com/sneha-510/failureforge.git
cd failureforge

make up                 # build & start all services
open http://localhost:3000
```

Run a failure and capture an incident:

```bash
make redis-outage       # also: make deadlock | memory-leak | slow-database
make incidents          # list captured incidents
```

### AI diagnosis

The diagnosis engine has two providers, selected by `DIAGNOSIS_PROVIDER`:

- **`gemini`** (default) — real LLM diagnosis. Add a key to a `.env` file at the
  repo root:

  ```
  GEMINI_API_KEY=your_key_here
  ```

- **`stub`** — an offline, deterministic diagnoser (no key needed), used for demos
  and tests:

  ```bash
  DIAGNOSIS_PROVIDER=stub docker compose -f docker/docker-compose.yml up -d --force-recreate orchestrator
  make demo            # runs all scenarios, diagnoses them, prints evaluation
  ```

Then `make evaluation` prints accuracy / precision / recall, and the dashboard
shows the per-scenario breakdown.

---

## Demo workflow

1. Launch the Redis Outage scenario (dashboard button or `make redis-outage`).
2. The orchestrator stops the Redis container.
3. The application service emits `connection refused` errors; latency rises.
4. Telemetry (logs + metrics) is collected for the incident window.
5. The incident is persisted to PostgreSQL and exported to `datasets/`.
6. The diagnosis engine analyzes the logs + metrics and produces a root-cause
   analysis.
7. The evaluation engine compares the prediction to the known ground truth and
   updates the benchmark metrics.

---

## Testing

```bash
make test            # unit tests (offline)
make e2e             # backend pipeline E2E (live stack, stub diagnosis provider)
make e2e-ui          # frontend Playwright E2E (full stack)
```

See [`docs/E2E.md`](docs/E2E.md) for details.

---

## Future roadmap

FailureForge is evolving toward a generalized reliability-engineering platform.
**The following is future work and is NOT yet implemented:**

- Accepting arbitrary containerized applications (upload a Docker Compose project).
- Automatic service-dependency discovery.
- Dynamic, dependency-aware fault injection.
- AI-generated resilience reports and reliability scoring.
- Remediation recommendations.

**Long-term vision:** a developer uploads a Docker Compose project and
automatically receives reliability assessments and failure-analysis reports.

See [`ROADMAP.md`](ROADMAP.md) for milestone detail. Contributions are welcome —
see [`CONTRIBUTING.md`](CONTRIBUTING.md).

## License

[MIT](LICENSE) © Sneha Choudhary
