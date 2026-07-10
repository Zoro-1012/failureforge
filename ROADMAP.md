# FailureForge Roadmap

This document describes planned milestones. Everything below is **future work**
and is **not yet implemented**. The shipped functionality is described in
[`README.md`](README.md).

The direction is to evolve FailureForge from a fixed-environment benchmark into a
generalized reliability-engineering platform that can analyze arbitrary
containerized applications.

---

## V1 — Shipped (current)

For reference, what exists today:

- Controlled distributed environment (application service + PostgreSQL + Redis).
- Four failure scenarios: Redis outage, database deadlock, memory leak, slow
  database.
- Telemetry collection (structured logs + metrics) and incident persistence in
  PostgreSQL, with portable dataset export.
- AI diagnosis engine (Gemini provider + offline deterministic provider).
- Evaluation engine (accuracy / precision / recall / F1, per scenario).
- Next.js dashboard, demo + E2E tooling, CI.

---

## V2 — Generalized fault injection

- **Docker Compose project ingestion** — point FailureForge at an arbitrary
  `docker-compose.yml` instead of the bundled environment.
- **Dependency graph generation** — discover services and their relationships
  (networks, links, ports) to understand the topology under test.
- **Dynamic fault injection** — inject failures into discovered services
  (stop/pause containers, add latency, exhaust resources) rather than relying on
  hard-coded scenarios.

## V3 — Automated reliability analysis

- **AI-generated resilience reports** — summarize how the system behaved across a
  battery of injected failures.
- **Automatic failure selection** — choose which faults to inject based on the
  discovered dependency graph and risk heuristics.
- **Reliability scoring** — produce a quantitative resilience score per service
  and per system.

## V4 — Scale & integrations

- **Kubernetes support** — inject failures into Kubernetes workloads (pod kills,
  network policies, resource limits) in addition to Docker.
- **Advanced observability integrations** — ingest telemetry from external
  observability backends rather than only the bundled collector.

---

## Notes

- Roadmap items are intentionally sequenced so each builds on the previous one
  (topology discovery → dynamic injection → automated analysis → scale).
- Generalizing beyond the controlled environment introduces an important caveat:
  for real/unlabeled systems there is no injected ground truth, so the platform
  shifts from *scoring* diagnoses to *generating* them — the evaluation layer will
  need an explicit "unlabeled incident" mode.
