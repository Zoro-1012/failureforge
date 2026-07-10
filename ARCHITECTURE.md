# FailureForge — Architecture

FailureForge simulates realistic distributed-systems failures, captures
observability data, asks an AI to diagnose the root cause, and scores that
diagnosis against known ground truth.

## Components

```mermaid
flowchart TB
    user([User])

    subgraph browser["Browser"]
        ui["Next.js Dashboard<br/>(ff-frontend :3000)<br/>totals · scenario runner · incident view"]
    end

    subgraph control["Control plane"]
        orch["Orchestrator API<br/>(ff-orchestrator :8000)<br/>FastAPI"]
        scen["Scenario runner"]
        tele["Telemetry collector"]
        diag["Gemini diagnosis engine"]
        evale["Evaluation engine"]
        orch --- scen
        orch --- tele
        orch --- diag
        orch --- evale
    end

    subgraph env["Distributed test environment"]
        app["Application service<br/>(ff-app :8001)<br/>read/write DB + cache, emits logs"]
        pg[("PostgreSQL<br/>ff-postgres")]
        redis[("Redis<br/>ff-redis")]
        app --> pg
        app --> redis
    end

    gemini{{"Gemini API<br/>(gemini-2.5-flash)"}}
    ds[["datasets/incident_NNN/<br/>logs · metrics · ground_truth · diagnosis"]]

    user --> ui
    ui -->|HTTP| orch
    scen -->|inject failure / drive load| app
    scen -->|stop/start containers via Docker socket| redis
    tele -->|probe latency + docker stats| app
    orch -->|incidents · logs · metrics · diagnoses| pg
    diag -->|logs + metrics only| gemini
    orch -->|export| ds
```

## Diagnosis & evaluation flow

```mermaid
sequenceDiagram
    actor U as User
    participant FE as Dashboard
    participant OR as Orchestrator
    participant APP as App service
    participant DK as Docker
    participant DB as PostgreSQL
    participant G as Gemini

    U->>FE: Click "Redis Outage"
    FE->>OR: POST /scenario/start
    OR->>APP: baseline load (/work)
    OR->>DK: stop ff-redis
    OR->>APP: failure load (/work) → ERROR logs, latency ↑
    OR->>DK: start ff-redis (recover)
    OR->>DB: persist incident (logs, metrics, ground_truth)
    OR-->>FE: incident_001

    U->>FE: Open incident → "Run AI diagnosis"
    FE->>OR: POST /diagnose/incident_001
    OR->>DB: fetch logs + metrics (no ground truth)
    OR->>G: telemetry context → RCA
    G-->>OR: {predicted_cause, confidence, evidence, fix}
    OR->>DB: save diagnosis
    OR-->>FE: diagnosis

    U->>FE: View dashboard
    FE->>OR: GET /evaluation
    OR->>DB: join incidents × latest diagnosis
    OR-->>FE: accuracy / precision / recall (overall + per scenario)
```

## Failure scenarios

| Scenario | Injection | Ground truth | Key symptom |
|---|---|---|---|
| Redis Outage | stop the `ff-redis` container | `redis_outage` | `Redis connection refused`, latency ↑ |
| Database Deadlock | concurrent opposite-order transactions | `database_deadlock` | `deadlock detected`, aborted txns |
| Memory Leak | retained allocations vs `256m` limit | `memory_leak` | `memory_percent` ↑, `OOM warning` |
| Slow Database | `pg_sleep` injected into `/work` | `slow_database` | high `request_latency` |

## Data model (PostgreSQL)

```mermaid
erDiagram
    incidents ||--o{ logs : has
    incidents ||--o{ metrics : has
    incidents ||--o{ diagnoses : has

    incidents {
        int id PK
        text label
        text scenario
        text ground_truth
        timestamptz started_at
        jsonb summary
    }
    logs {
        int id PK
        int incident_id FK
        text severity
        text message
    }
    metrics {
        int id PK
        int incident_id FK
        text phase
        real request_latency
        real memory_percent
    }
    diagnoses {
        int id PK
        int incident_id FK
        text predicted_cause
        real confidence
        jsonb evidence
        text model
    }
```

See `docs/PHASE1.md`–`docs/PHASE5.md` for per-phase detail.
