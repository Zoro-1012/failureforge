"""Phase 3 tests for the AI diagnosis pipeline.

These are pure-logic tests (no network / no API key needed): they cover context
construction, output parsing, and validation. The live Gemini call is exercised
by the end-to-end flow in test_e2e_diagnose (skipped unless GEMINI_API_KEY is set
and the stack is running).
"""
import importlib.util
import os

import pytest

# Load the diagnosis module directly so these tests run without the full package
# (and without importing psycopg2 / docker via the package __init__ chain).
_spec = importlib.util.spec_from_file_location(
    "diagnosis",
    os.path.join(os.path.dirname(__file__), "..", "backend", "orchestrator",
                 "diagnosis.py"),
)


def _load():
    # diagnosis.py imports `.logging_config`; provide a tiny stub package context.
    import sys
    import types

    pkg = types.ModuleType("orchestrator")
    pkg.__path__ = []
    sys.modules.setdefault("orchestrator", pkg)
    lc = types.ModuleType("orchestrator.logging_config")
    import logging
    lc.get_logger = lambda: logging.getLogger("test")
    sys.modules["orchestrator.logging_config"] = lc

    spec = importlib.util.spec_from_file_location(
        "orchestrator.diagnosis",
        os.path.join(os.path.dirname(__file__), "..", "backend", "orchestrator",
                     "diagnosis.py"),
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["orchestrator.diagnosis"] = mod
    spec.loader.exec_module(mod)
    return mod


diagnosis = _load()


SAMPLE_INCIDENT = {
    "incident_id": "incident_001",
    "logs": [
        {"severity": "ERROR", "message": "Redis connection refused: cache unavailable"},
        {"severity": "ERROR", "message": "Redis connection refused: cache unavailable"},
        {"severity": "INFO", "message": "served /work"},
    ],
    "metrics": [
        {"phase": "baseline", "request_latency": 5.0, "memory_percent": 10.0, "cpu_percent": 2.0},
        {"phase": "failure", "request_latency": 80.0, "memory_percent": 11.0, "cpu_percent": 3.0},
    ],
}


def test_build_context_includes_signals_not_ground_truth():
    ctx = diagnosis.build_context(SAMPLE_INCIDENT)
    assert "Redis connection refused" in ctx
    assert "metrics_failure" in ctx and "metrics_baseline" in ctx
    # The ground-truth label must never be leaked to the model.
    assert "redis_outage" not in ctx
    assert "ground_truth" not in ctx


def test_parse_valid_json():
    raw = (
        '{"predicted_cause":"redis_outage","confidence":0.93,'
        '"evidence":["Redis connection refused logs","latency rose 16x"],'
        '"recommended_fix":"restart redis and add a circuit breaker"}'
    )
    out = diagnosis._parse(raw)
    assert out["predicted_cause"] == "redis_outage"
    assert out["confidence"] == 0.93
    assert isinstance(out["evidence"], list) and len(out["evidence"]) == 2
    assert out["recommended_fix"]


def test_parse_handles_code_fences_and_clamps_confidence():
    raw = '```json\n{"predicted_cause":"memory_leak","confidence":1.7,"evidence":"x"}\n```'
    out = diagnosis._parse(raw)
    assert out["predicted_cause"] == "memory_leak"
    assert out["confidence"] == 1.0  # clamped to [0,1]
    assert out["evidence"] == ["x"]  # coerced to list


def test_parse_rejects_garbage():
    with pytest.raises(diagnosis.DiagnosisError):
        diagnosis._parse("not json at all")


def test_diagnose_without_key_raises():
    os.environ.pop("GEMINI_API_KEY", None)
    os.environ.pop("DIAGNOSIS_PROVIDER", None)
    with pytest.raises(diagnosis.DiagnosisError):
        diagnosis.diagnose(SAMPLE_INCIDENT)


# --- stub provider (offline, deterministic) ---------------------------------
STUB_CASES = {
    "redis_outage": "Redis connection refused: cache unavailable",
    "database_deadlock": "deadlock detected: transaction aborted",
    "memory_leak": "OOM warning: memory usage high (165 MB retained)",
    "slow_database": "slow database query: artificial delay 1.0s",
}


@pytest.mark.parametrize("expected,message", list(STUB_CASES.items()))
def test_stub_provider_maps_symptoms(expected, message, monkeypatch):
    monkeypatch.setenv("DIAGNOSIS_PROVIDER", "stub")
    incident = {
        "incident_id": "incident_001",
        "logs": [{"severity": "ERROR", "message": message}],
        "metrics": [{"phase": "failure", "memory_percent": 62.0, "request_latency": 1080}],
    }
    out = diagnosis.diagnose(incident)
    assert out["predicted_cause"] == expected
    assert out["confidence"] == 0.9
    assert out["model"] == "stub-heuristic"


def test_stub_provider_unknown_signal(monkeypatch):
    monkeypatch.setenv("DIAGNOSIS_PROVIDER", "stub")
    out = diagnosis.diagnose({"incident_id": "x", "logs": [], "metrics": []})
    assert out["predicted_cause"] == ""
    assert out["confidence"] == 0.0
