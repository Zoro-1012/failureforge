# Contributing to FailureForge

Thanks for your interest in contributing! This guide covers local setup, how the
project is organized, and the conventions to follow.

## Development setup

Requirements: Docker Desktop (with Compose), and — for running tests on the host —
Python 3.12+ and Node 20+.

```bash
git clone https://github.com/sneha-510/failureforge.git
cd failureforge
make up                 # build & start all services
open http://localhost:3000
```

Useful targets (`make help` lists them all):

| Command | Purpose |
|---|---|
| `make up` / `make down` | Start / stop the stack |
| `make redis-outage` (etc.) | Run a single scenario |
| `make demo` | Run all scenarios, diagnose, print evaluation |
| `make evaluation` | Print benchmark metrics |
| `make test` | Unit tests (offline) |
| `make e2e` / `make e2e-ui` | Backend / frontend end-to-end tests |

## Project structure

- `backend/app/` — the application service under test (FastAPI). It performs DB +
  cache work and exposes the hooks the orchestrator uses to inject failures.
- `backend/orchestrator/` — the control plane: `scenarios.py` (failure injection),
  `telemetry.py`, `db_store.py` (PostgreSQL), `storage.py` (dataset export),
  `diagnosis.py` (AI diagnosis), `evaluation.py` (metrics), `main.py` (API).
- `frontend/` — Next.js 15 + TypeScript + Tailwind dashboard.
- `tests/` — Pytest. Unit tests run offline; `tests/test_scenarios.py` and
  `tests/e2e/` require a running stack and skip automatically otherwise.

See [`ARCHITECTURE.md`](ARCHITECTURE.md) for diagrams.

## Conventions

- **Diagnosis providers** — `DIAGNOSIS_PROVIDER=gemini` (default) or `stub`
  (offline deterministic). New tests should prefer the stub provider so they run
  without an API key.
- **Cause taxonomy** — keep `scenarios.SCENARIOS`, `diagnosis.KNOWN_CAUSES`, and
  `evaluation.LABELS` in sync when adding a scenario; there is a test guarding
  this.
- **No secrets in the repo** — configuration goes through environment variables;
  use `.env` (gitignored) locally and update `.env.example` for any new variable.
- **Python** — standard library logging with the structured JSON formatter; keep
  functions small and testable (pure logic separated from I/O where practical).
- **TypeScript** — `npm run lint` should pass; keep API types in `frontend/lib/api.ts`.

## Adding a new failure scenario

1. Add the injection hook to `backend/app/` (an endpoint or behavior the
   orchestrator can trigger).
2. Add an injector + register it in `backend/orchestrator/scenarios.py`.
3. Add the label to `diagnosis.KNOWN_CAUSES`, `evaluation.LABELS`, and the stub
   heuristic in `diagnosis.py`.
4. Add a button to the frontend scenario runner.
5. Add tests (unit + a live-stack assertion).

## Pull requests

1. Fork and create a feature branch.
2. Ensure `make test` passes and the stack builds (`make up`).
3. Keep changes focused; update docs (`README.md`, `docs/`) when behavior changes.
4. Open a PR describing the change and how you verified it.

## Roadmap

Larger initiatives are tracked in [`ROADMAP.md`](ROADMAP.md). Note that roadmap
items (Compose ingestion, dependency discovery, etc.) are **not yet implemented** —
contributions toward them are especially welcome.
