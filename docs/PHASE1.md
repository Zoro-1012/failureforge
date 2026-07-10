# Phase 1 — One real failure, end-to-end

**Deliverable:** Docker Compose + Redis Outage scenario + structured logging, with
a benchmark incident written to `datasets/`.

## What's included

- **Application service** (`backend/app`) — FastAPI service that reads/writes
  PostgreSQL and Redis and emits canonical JSON logs (`timestamp`, `service`,
  `severity`, `message`). `/work` performs a read-through cache operation; when
  Redis is unavailable it logs `Redis connection refused` and falls back to the DB.
- **Orchestrator** (`backend/orchestrator`) — control plane that runs scenarios,
  controls containers via the Docker socket, samples telemetry, and persists
  incidents. Endpoints: `POST /scenario/start`, `GET /incidents`,
  `GET /incidents/{id}`, `GET /health`.
- **Redis Outage scenario** (`scenarios.run_redis_outage`) — baseline → stop
  `ff-redis` → observe under load → restart Redis → persist the incident.
- **Telemetry** — `cpu_percent`, `memory_percent`, `request_latency` per sample,
  tagged `baseline` / `failure`.
- **Benchmark dataset** — `datasets/incident_NNN/{logs,metrics,ground_truth}.json`.

## How the failure becomes observable

The Redis client uses a 1s connect/socket timeout, so when the container stops,
cache calls fail fast with `redis.ConnectionError`. The app logs these at ERROR
and falls back to PostgreSQL, which raises per-request latency. The orchestrator
captures both signals (ERROR logs + rising latency) and the ground truth label.

## Run it

```bash
make up            # build + start postgres, redis, app, orchestrator
make redis-outage  # run the scenario (~15s)
make incidents     # list captured incidents
cat datasets/incident_001/ground_truth.json
make test          # pytest end-to-end checks
make down          # stop
```

## Verifying success

1. `make ps` shows four healthy containers.
2. The `/scenario/start` response shows `error_log_count > 0` and
   `avg_failure_latency_ms >= avg_baseline_latency_ms`.
3. `datasets/incident_001/` exists with the three JSON files; ground truth is
   `redis_outage`.

## Roadmap (not in Phase 1)

- **Phase 2** — remaining scenarios (database_deadlock, memory_leak,
  slow_database) + persistent telemetry storage in PostgreSQL.
- **Phase 3** — Gemini diagnosis pipeline (`POST /diagnose/{incident_id}`).
- **Phase 4** — evaluation engine (accuracy / precision / recall per scenario).
- **Phase 5** — Next.js dashboard + docs + demo.

The orchestration loop and dataset format are intentionally generic so Phase 2
scenarios slot into the same structure.
