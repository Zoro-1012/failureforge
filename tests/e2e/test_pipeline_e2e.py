"""Backend pipeline end-to-end test.

Exercises the full flow against a LIVE stack:

    start scenario -> incident persisted -> diagnose -> evaluation

Run it via `scripts/e2e.sh`, which boots the stack with the offline stub
diagnosis provider (DIAGNOSIS_PROVIDER=stub) so results are deterministic and no
Gemini key is required. When the stub provider is in use, set E2E_STUB=1 so the
test asserts each prediction exactly matches ground truth.

Skips automatically if the orchestrator is not reachable.
"""
import os

import httpx
import pytest

ORCHESTRATOR = os.getenv("ORCHESTRATOR_URL", "http://localhost:8000")
EXPECT_EXACT = os.getenv("E2E_STUB") == "1"

SCENARIOS = ["redis_outage", "database_deadlock", "memory_leak", "slow_database"]


def _stack_up() -> bool:
    try:
        return httpx.get(f"{ORCHESTRATOR}/health", timeout=3.0).status_code == 200
    except httpx.HTTPError:
        return False


pytestmark = pytest.mark.skipif(
    not _stack_up(), reason="orchestrator not reachable; run scripts/e2e.sh"
)


@pytest.fixture(scope="module")
def captured() -> dict:
    """Run every scenario once and diagnose each; return {scenario: incident_id}."""
    ids: dict = {}
    with httpx.Client(base_url=ORCHESTRATOR, timeout=180.0) as client:
        for scenario in SCENARIOS:
            r = client.post("/scenario/start", json={"scenario": scenario})
            assert r.status_code == 200, r.text
            incident_id = r.json()["incident_id"]
            ids[scenario] = incident_id

            d = client.post(f"/diagnose/{incident_id}")
            assert d.status_code == 200, d.text
    return ids


def test_incidents_persisted_with_telemetry(captured):
    with httpx.Client(base_url=ORCHESTRATOR, timeout=30.0) as client:
        for scenario, incident_id in captured.items():
            detail = client.get(f"/incidents/{incident_id}").json()
            assert detail["ground_truth"]["ground_truth"] == scenario
            assert len(detail["logs"]) > 0
            assert len(detail["metrics"]) > 0
            assert detail["diagnosis"] is not None


def test_diagnoses_are_in_taxonomy(captured):
    taxonomy = set(SCENARIOS)
    with httpx.Client(base_url=ORCHESTRATOR, timeout=30.0) as client:
        for scenario, incident_id in captured.items():
            detail = client.get(f"/incidents/{incident_id}").json()
            predicted = detail["diagnosis"]["predicted_cause"]
            assert predicted in taxonomy
            if EXPECT_EXACT:
                assert predicted == scenario, (
                    f"{incident_id}: predicted {predicted}, expected {scenario}"
                )


def test_evaluation_reflects_runs(captured):
    ev = httpx.get(f"{ORCHESTRATOR}/evaluation", timeout=30.0).json()
    assert ev["evaluated"] >= len(SCENARIOS)
    assert 0.0 <= ev["overall"]["accuracy"] <= 1.0
    if EXPECT_EXACT:
        # Deterministic stub diagnoses every generated incident correctly.
        assert ev["overall"]["accuracy"] == 1.0
        for scenario in SCENARIOS:
            assert ev["per_scenario"][scenario]["recall"] == 1.0
