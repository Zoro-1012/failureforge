"""Orchestrator API — the control plane for FailureForge.

Endpoints (Phase 1–2):
  POST /scenario/start    launch a failure scenario (all four supported)
  GET  /scenarios         list available scenarios
  GET  /incidents         list captured incidents (from PostgreSQL)
  GET  /incidents/{id}    full incident detail (logs + metrics + ground truth)

Diagnosis (POST /diagnose) and evaluation (GET /evaluation) arrive in later phases.
"""
import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from . import (
    db_store,
    diagnosis,
    docker_control,
    evaluation,
    scenarios,
    storage,
)
from .logging_config import get_logger

log = get_logger()
app = FastAPI(title="FailureForge Orchestrator")

# Allow the Next.js dashboard (default localhost:3000) to call the API.
_origins = os.getenv(
    "CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
).split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _origins if o.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ScenarioRequest(BaseModel):
    scenario: str = "redis_outage"


@app.on_event("startup")
def _startup() -> None:
    try:
        db_store.init_schema()
        log.info("telemetry store ready")
    except Exception as err:  # don't crash the API if DB is briefly unavailable
        log.error("could not init telemetry store: %s", err)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "redis": docker_control.container_status(docker_control.REDIS_CONTAINER),
        "app": docker_control.container_status(docker_control.APP_CONTAINER),
    }


@app.get("/scenarios")
def list_scenarios():
    return {"scenarios": sorted(scenarios.SCENARIOS)}


@app.post("/scenario/start")
def start_scenario(req: ScenarioRequest):
    if req.scenario not in scenarios.SCENARIOS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown scenario '{req.scenario}'. "
            f"Available: {sorted(scenarios.SCENARIOS)}",
        )
    try:
        return scenarios.run_scenario(req.scenario)
    except Exception as err:
        log.error("scenario failed: %s", err)
        # Best-effort recovery: ensure Redis is back if a scenario left it down.
        try:
            docker_control.start_container(docker_control.REDIS_CONTAINER)
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=str(err))


@app.get("/incidents")
def incidents():
    return {"incidents": db_store.list_incidents()}


@app.get("/incidents/{incident_id}")
def incident_detail(incident_id: str):
    incident = db_store.get_incident(incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="incident not found")
    return incident


@app.post("/diagnose/{incident_id}")
def diagnose_incident(incident_id: str):
    """Run the Gemini RCA pipeline over a stored incident and persist the result."""
    incident = db_store.get_incident(incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="incident not found")
    try:
        result = diagnosis.diagnose(incident)
    except diagnosis.DiagnosisError as err:
        raise HTTPException(status_code=502, detail=str(err))

    saved = db_store.save_diagnosis(incident_id, result)
    storage.export_diagnosis(incident_id, result)
    log.info("diagnosed %s -> %s (%.2f)", incident_id,
             result["predicted_cause"], result["confidence"])
    return saved


@app.get("/evaluation")
def evaluation_metrics():
    """Benchmark metrics: accuracy / precision / recall, overall and per scenario."""
    return evaluation.evaluate()
