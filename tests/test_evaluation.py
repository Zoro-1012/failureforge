"""Phase 4 tests for the evaluation metric math (pure, no DB)."""
import importlib.util
import os
import sys
import types


def _load():
    # evaluation.py does `from . import db_store`; stub it so import works
    # without psycopg2.
    pkg = types.ModuleType("orchestrator")
    pkg.__path__ = []
    sys.modules.setdefault("orchestrator", pkg)
    db_stub = types.ModuleType("orchestrator.db_store")
    db_stub.get_eval_pairs = lambda: []
    sys.modules["orchestrator.db_store"] = db_stub

    spec = importlib.util.spec_from_file_location(
        "orchestrator.evaluation",
        os.path.join(os.path.dirname(__file__), "..", "backend", "orchestrator",
                     "evaluation.py"),
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["orchestrator.evaluation"] = mod
    spec.loader.exec_module(mod)
    return mod


ev = _load()


def test_perfect_predictions():
    recs = [
        {"actual": "redis_outage", "predicted": "redis_outage"},
        {"actual": "memory_leak", "predicted": "memory_leak"},
    ]
    out = ev.compute(recs)
    assert out["overall"]["accuracy"] == 1.0
    assert out["per_scenario"]["redis_outage"]["recall"] == 1.0
    assert out["per_scenario"]["redis_outage"]["precision"] == 1.0


def test_known_confusion_precision_recall():
    # 3 redis (2 right, 1 called slow_database), 2 slow_database (both right).
    recs = [
        {"actual": "redis_outage", "predicted": "redis_outage"},
        {"actual": "redis_outage", "predicted": "redis_outage"},
        {"actual": "redis_outage", "predicted": "slow_database"},
        {"actual": "slow_database", "predicted": "slow_database"},
        {"actual": "slow_database", "predicted": "slow_database"},
    ]
    out = ev.compute(recs)
    # overall accuracy = 4/5
    assert out["overall"]["accuracy"] == 0.8

    redis = out["per_scenario"]["redis_outage"]
    assert redis["support"] == 3
    assert redis["recall"] == round(2 / 3, 4)      # 2 of 3 redis caught
    assert redis["precision"] == 1.0               # everything called redis WAS redis

    slow = out["per_scenario"]["slow_database"]
    assert slow["recall"] == 1.0                    # both slow caught
    assert slow["precision"] == round(2 / 3, 4)     # 1 redis mislabelled as slow

    # confusion matrix entry
    assert out["confusion_matrix"]["redis_outage"]["slow_database"] == 1


def test_out_of_taxonomy_prediction_counts_as_miss():
    recs = [
        {"actual": "memory_leak", "predicted": "cosmic_rays"},
        {"actual": "memory_leak", "predicted": "memory_leak"},
    ]
    out = ev.compute(recs)
    assert out["overall"]["accuracy"] == 0.5
    assert out["per_scenario"]["memory_leak"]["recall"] == 0.5
    # the unknown label shows up in the confusion matrix
    assert out["confusion_matrix"]["memory_leak"]["cosmic_rays"] == 1


def test_empty_is_safe():
    out = ev.compute([])
    assert out["evaluated"] == 0
    assert out["overall"]["accuracy"] == 0.0


def test_evaluate_wires_storage(monkeypatch=None):
    # Swap the stubbed get_eval_pairs to include one undiagnosed incident.
    ev.db_store.get_eval_pairs = lambda: [
        {"incident_id": "incident_001", "ground_truth": "redis_outage",
         "predicted_cause": "redis_outage", "confidence": 0.9},
        {"incident_id": "incident_002", "ground_truth": "memory_leak",
         "predicted_cause": None, "confidence": None},
    ]
    out = ev.evaluate()
    assert out["total_incidents"] == 2
    assert out["undiagnosed"] == 1
    assert out["evaluated"] == 1
    assert out["overall"]["accuracy"] == 1.0
