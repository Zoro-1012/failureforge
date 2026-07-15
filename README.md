<h1 align="center">⚒️ FailureForge</h1>

<p align="center">
An AI-powered distributed systems failure simulation and LLM evaluation platform.
</p>

<p align="center">
Generate infrastructure failures • Capture real telemetry • Diagnose with AI • Benchmark against Ground Truth
</p>

<p align="center">

![Python](https://img.shields.io/badge/Python-3.11-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-green)
![Next.js](https://img.shields.io/badge/Next.js-15-black)
![Docker](https://img.shields.io/badge/Docker-Compose-blue)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Database-blue)
![Redis](https://img.shields.io/badge/Redis-Cache-red)
![Gemini](https://img.shields.io/badge/Gemini-AI-purple)
![License](https://img.shields.io/github/license/Zoro-1012/failureforge)

</p>

---

# 🚀 Why FailureForge?

Modern LLMs can summarize logs, but can they accurately identify the real root cause of infrastructure failures?

FailureForge creates controlled failures inside a distributed environment, captures production-like telemetry, diagnoses incidents using AI, and evaluates the diagnosis against the known ground truth.

Because every incident is intentionally injected, the true root cause is always known—making diagnostic benchmarking objective and reproducible.

---

# ✨ Highlights

- ⚡ Docker-based distributed environment
- 🤖 AI-powered root cause analysis
- 📊 Automatic benchmark generation
- 📈 Precision / Recall / F1 evaluation
- 🔬 Reproducible experiments
- 📦 Exportable benchmark datasets
- 🧪 End-to-end tested
- 🌐 Interactive Next.js dashboard

---

# 📌 Features

| Feature | Status |
|---------|--------|
| Redis Outage Simulation | ✅ |
| PostgreSQL Deadlock Simulation | ✅ |
| Memory Leak Simulation | ✅ |
| Slow Database Simulation | ✅ |
| Telemetry Collection | ✅ |
| Incident Persistence | ✅ |
| AI Diagnosis Engine | ✅ |
| Evaluation Framework | ✅ |
| Interactive Dashboard | ✅ |

---

# 🏗 Architecture

```text
        User
          │
          ▼
  Next.js Dashboard
          │
          ▼
 FastAPI Backend / Orchestrator
          │
          ▼
 Failure Orchestrator
          │
          ▼
 Distributed Environment
 (App + PostgreSQL + Redis)
          │
          ▼
 Telemetry Collection
          │
          ▼
 PostgreSQL
          │
          ▼
 AI Diagnosis Engine
          │
          ▼
 Evaluation Engine
```

A complete architecture diagram with Mermaid visualizations is available in **ARCHITECTURE.md**.

---

# 📷 Dashboard Preview

### Home

![Home](docs/images/home.png)

### Incident Details

![Incident](docs/images/incident.png)

### Benchmark Metrics

![Metrics](docs/images/metrics.png)

---

# ⚙ Tech Stack

## Backend

- Python
- FastAPI

## Frontend

- Next.js 15
- TypeScript
- Tailwind CSS

## Infrastructure

- Docker
- Docker Compose

## Database

- PostgreSQL
- Redis

## AI

- Gemini API

## Testing

- Pytest
- Playwright

---

# 📂 Repository Structure

```text
backend/
 ├── app/
 ├── orchestrator/

frontend/

docker/

datasets/

scripts/

docs/

tests/
```

---

# 🚀 Quick Start

## Clone Repository

```bash
git clone https://github.com/Zoro-1012/failureforge.git

cd failureforge
```

## Start Everything

```bash
make up
```

Open

```
http://localhost:3000
```

---

# 🚨 Run Failure Scenarios

Redis Outage

```bash
make redis-outage
```

Database Deadlock

```bash
make deadlock
```

Memory Leak

```bash
make memory-leak
```

Slow Database

```bash
make slow-database
```

List captured incidents

```bash
make incidents
```

---

# 🤖 AI Diagnosis

FailureForge supports two diagnosis providers.

## Gemini

Create a `.env`

```env
GEMINI_API_KEY=your_api_key
```

---

## Offline Stub

```bash
DIAGNOSIS_PROVIDER=stub docker compose -f docker/docker-compose.yml up -d --force-recreate orchestrator

make demo
```

Generate benchmark metrics

```bash
make evaluation
```

---

# 🔄 Demo Workflow

1. Launch a failure scenario.
2. Infrastructure failure is injected.
3. Application emits logs and metrics.
4. Telemetry is captured.
5. Incident is stored in PostgreSQL.
6. AI generates root cause analysis.
7. Evaluation compares prediction with ground truth.
8. Benchmark metrics are updated.

---

# 🧪 Testing

```bash
make test
```

Backend End-to-End

```bash
make e2e
```

Frontend Playwright

```bash
make e2e-ui
```

---

# 📈 Future Roadmap

Planned features include:

- Upload any Docker Compose application
- Automatic dependency discovery
- Dynamic fault injection
- AI-generated resilience reports
- Reliability scoring
- Automated remediation recommendations

---

# 🎯 Motivation

Current AI benchmarks evaluate language understanding.

FailureForge evaluates whether an AI model can accurately diagnose distributed system failures using real infrastructure telemetry.

It bridges the gap between Reliability Engineering, Chaos Engineering, Observability, and Generative AI.

---

# 🤝 Contributing

Contributions, ideas, and feature requests are always welcome.

Please check **CONTRIBUTING.md** before submitting a pull request.

---

# ⭐ If you found this project useful

Please consider giving the repository a **Star ⭐**.
