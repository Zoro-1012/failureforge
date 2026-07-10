"""Phase 2 end-to-end tests — all four scenarios reproducible.

Run against a live stack (`make up`):

    make test        # or: python -m pytest tests -v

Each scenario is driven through the orchestrator; we assert the incident was
persisted with the right ground truth and the expected symptoms.
"""
import os

import httpx
import pytest

ORCHESTRATOR = os.getenv("ORCHESTRATOR_URL", "http://localhost:8000")


def _stack_up() -> bool:
    try:
        return httpx.get(f"{ORCHESTRATOR}/health", timeout=3.0).status_code == 200
    except httpx.HTTPError:
        return False


pytestmark = pytest.mark.skipif(
    not _stack_up(), reason="orchestrator not reachable; run `make up` first"
)


def _run(scenario: str) -> dict:
    resp = httpx.post(
        f"{ORCHESTRATOR}/scenario/start",
        json={"scenario": scenario},
        timeout=180.0,
    )
    assert resp.status_code == 200, resp.text
    incident = resp.json()
    assert incident["ground_truth"] == scenario
    assert incident["log_count"] > 0 and incident["metric_count"] > 0
    return incident


def test_all_scenarios_listed():
    listing = httpx.get(f"{ORCHESTRATOR}/scenarios", timeout=10.0).json()
    assert set(listing["scenarios"]) == {
        "redis_outage", "database_deadlock", "memory_leak", "slow_database"
    }


def test_redis_outage():
    inc = _run("redis_outage")
    assert inc["summary"]["error_log_count"] > 0
    assert inc["summary"]["avg_failure_latency_ms"] >= inc["summary"]["avg_baseline_latency_ms"]


def test_database_deadlock():
    inc = _run("database_deadlock")
    # Deadlock detection surfaces as ERROR logs.
    assert inc["summary"]["error_log_count"] > 0
    detail = httpx.get(
        f"{ORCHESTRATOR}/incidents/{inc['incident_id']}", timeout=10.0
    ).json()
    assert any("deadlock" in l["message"].lower() for l in detail["logs"])


def test_memory_leak():
    inc = _run("memory_leak")
    # Memory rises during the failure phase and OOM warnings are emitted.
    assert inc["summary"]["max_failure_memory_percent"] >= \
        (inc["summary"]["max_baseline_memory_percent"] or 0)
    assert inc["summary"]["warning_log_count"] > 0


def test_slow_database():
    inc = _run("slow_database")
    # Artificial delays push failure-phase latency well above baseline.
    assert inc["summary"]["avg_failure_latency_ms"] > inc["summary"]["avg_baseline_latency_ms"]


def test_incidents_persisted_in_db():
    listing = httpx.get(f"{ORCHESTRATOR}/incidents", timeout=10.0).json()
    assert listing["incidents"], "expected captured incidents in PostgreSQL"
    grounds = {i["ground_truth"] for i in listing["incidents"]}
    assert grounds, grounds


def test_unknown_scenario_rejected():
    resp = httpx.post(
        f"{ORCHESTRATOR}/scenario/start", json={"scenario": "nope"}, timeout=10.0
    )
    assert resp.status_code == 400
