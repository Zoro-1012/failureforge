# Phase 2 — All four failures reproducible + persistent telemetry

**Deliverable:** every failure scenario reproducible end-to-end, with telemetry
persisted in PostgreSQL (no longer just flat files).

## What's new since Phase 1

- **Three more scenarios**, behind one generic orchestration loop
  (`scenarios.run_scenario`): `database_deadlock`, `memory_leak`, `slow_database`.
- **Persistent telemetry storage** (`db_store.py`): incidents, logs, and metrics
  are written to PostgreSQL — now the system of record. The portable benchmark
  dataset is still exported to `datasets/incident_NNN/` alongside.
- **App control hooks** the orchestrator uses to inject failures:
  `POST /config/slow`, `GET /deadlock`, `POST /leak`, `POST /leak/reset`.
- **Bounded app memory** (`mem_limit: 256m`) so the leak produces a meaningful
  `memory_percent` and an OOM warning without killing the container.

## How each scenario is simulated

| Scenario | Injection | Observable symptoms |
|---|---|---|
| `redis_outage` | stop the `ff-redis` container | ERROR `Redis connection refused`, latency rises |
| `database_deadlock` | fire `/deadlock?order=ab` and `?order=ba` concurrently (opposite lock orders) | ERROR `deadlock detected`, aborted transactions |
| `memory_leak` | repeated `POST /leak` retains memory | `memory_percent` climbs, WARNING `OOM warning` |
| `slow_database` | `POST /config/slow` injects `pg_sleep` into `/work` | high `request_latency`, slow-query warnings |

Each run: **baseline → inject + observe → recover → persist**. Recovery restores
the environment (restart Redis, free leaked memory, disable slow mode) so the
stack stays reusable for the next scenario.

## Telemetry schema (PostgreSQL)

```
incidents(id, label, scenario, ground_truth, started_at, log_count, metric_count, summary)
logs(id, incident_id, ts, service, severity, message)
metrics(id, incident_id, ts, phase, cpu_percent, memory_percent, request_latency, request_ok)
```

`label` (e.g. `incident_003`) is assigned from the incident's serial id and is
shared by the DB row and the exported dataset folder.

## Run it

```bash
make up                 # build + start the stack
make all-scenarios      # run all four (or: make redis-outage / deadlock / memory-leak / slow-database)
make incidents          # list incidents from PostgreSQL
make test               # pytest: asserts each scenario's symptoms + persistence
ls datasets/            # exported benchmark datasets
```

## Verifying success

1. `GET /scenarios` returns all four names.
2. Each `POST /scenario/start` returns a summary showing the expected signal
   (error/warning counts, latency or memory rising in the failure phase).
3. `GET /incidents` lists incidents read back from PostgreSQL.
4. `datasets/` contains one folder per run with `logs/metrics/ground_truth.json`.

## Roadmap (next)

- **Phase 3** — Gemini diagnosis pipeline (`POST /diagnose/{incident_id}`) consuming
  the stored logs + metrics.
- **Phase 4** — evaluation engine (accuracy / precision / recall per scenario).
- **Phase 5** — Next.js dashboard + docs + demo.
