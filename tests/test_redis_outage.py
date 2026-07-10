"""Focused offline checks for the Redis Outage path.

The live end-to-end Redis Outage flow is covered in tests/test_scenarios.py and
tests/e2e/. These are fast, dependency-light unit checks (no stack, no API key)
that the Redis Outage symptom signature maps to the correct cause label and that
the cause taxonomy is consistent across modules.
"""
import importlib.util
import logging
import os
import sys
import types


def _load(module: str):
    """Load an orchestrator module in isolation with heavy deps stubbed."""
    pkg = types.ModuleType("orchestrator")
    pkg.__path__ = []
    sys.modules.setdefault("orchestrator", pkg)

    lc = types.ModuleType("orchestrator.logging_config")
    lc.get_logger = lambda: logging.getLogger("test")
    sys.modules["orchestrator.logging_config"] = lc

    db = types.ModuleType("orchestrator.db_store")
    db.get_eval_pairs = lambda: []
    sys.modules["orchestrator.db_store"] = db

    path = os.path.join(os.path.dirname(__file__), "..", "backend", "orchestrator",
                        f"{module}.py")
    spec = importlib.util.spec_from_file_location(f"orchestrator.{module}", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[f"orchestrator.{module}"] = mod
    spec.loader.exec_module(mod)
    return mod


diagnosis = _load("diagnosis")
evaluation = _load("evaluation")


def test_redis_outage_symptom_maps_to_cause(monkeypatch):
    monkeypatch.setenv("DIAGNOSIS_PROVIDER", "stub")
    incident = {
        "incident_id": "incident_001",
        "logs": [
            {"severity": "ERROR", "message": "Redis connection refused: cache unavailable"},
        ],
        "metrics": [
            {"phase": "baseline", "request_latency": 5.0},
            {"phase": "failure", "request_latency": 80.0},
        ],
    }
    out = diagnosis.diagnose(incident)
    assert out["predicted_cause"] == "redis_outage"
    assert out["confidence"] > 0


def test_redis_outage_in_shared_taxonomy():
    assert "redis_outage" in diagnosis.KNOWN_CAUSES
    assert "redis_outage" in evaluation.LABELS
    # The diagnosis taxonomy and the evaluation taxonomy must stay in sync.
    assert set(diagnosis.KNOWN_CAUSES) == set(evaluation.LABELS)
