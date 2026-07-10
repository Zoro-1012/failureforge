# Phase 5 — Dashboard, docs & demo

**Deliverable:** a portfolio-ready project — a web dashboard over the full
pipeline, plus documentation.

## What's new

- **Next.js 15 + TypeScript + Tailwind** frontend in `frontend/`.
- **CORS** enabled on the orchestrator so the browser app can call the API.
- **`frontend` service** added to Docker Compose (port 3000).

## Pages

- **Dashboard (`/`)** — totals (incidents, overall accuracy, macro F1,
  undiagnosed), an accuracy-by-scenario table (support / accuracy / precision /
  recall / F1), and the incident list.
- **Scenario runner** — four buttons (Redis Outage, Database Deadlock, Memory
  Leak, Slow Database) that launch a scenario and refresh the dashboard.
- **Incident view (`/incidents/[id]`)** — logs, metrics, the AI diagnosis
  (predicted cause, confidence, evidence, recommended fix), the ground truth, and
  a ✓/✗ evaluation result comparing them. Includes a "Run AI diagnosis" button
  for undiagnosed incidents.

## Architecture

```
Browser ──HTTP──▶ Next.js (ff-frontend :3000)
   └────────────▶ Orchestrator API (ff-orchestrator :8000) ──▶ Postgres / Redis / app
```

`NEXT_PUBLIC_API_URL` is inlined at build time and must be the orchestrator's
**host-published** address (`http://localhost:8000`), because the fetch runs in
the user's browser, not inside the Docker network.

## Run it

Everything in Docker:

```bash
make up                 # builds backend + frontend
open http://localhost:3000
```

Or run the frontend locally against a Dockerized backend:

```bash
make up                 # backend services
make web                # npm install + next dev on :3000
```

## Demo script (suggested)

1. Open the dashboard — empty state.
2. Click each scenario button to capture four incidents.
3. Open an incident → "Run AI diagnosis" → show predicted cause vs ground truth
   and the ✓ result.
4. Return to the dashboard → accuracy and per-scenario breakdown now populated.
5. Re-run scenarios a few times to show metrics stabilising.

## Success criteria (MVP complete)

A user can: launch a failure scenario, observe logs and metrics, run AI
diagnosis, compare it with known ground truth, and view benchmark accuracy — all
from the dashboard. ✅
