"""Benchmark dataset file export.

PostgreSQL (db_store) is the system of record. This module additionally exports
each incident as a portable, version-controllable benchmark dataset:

    datasets/incident_NNN/
        logs.json          captured app logs during the incident window
        metrics.json       telemetry samples (baseline + failure)
        ground_truth.json  the known root cause + metadata

The incident label is assigned by db_store so the DB row and the dataset folder
always share the same id.
"""
import json
import os

DATASETS_DIR = os.getenv("DATASETS_DIR", "/datasets")


def export_incident(label: str, scenario: str, ground_truth: str,
                   logs: list, metrics: list) -> str:
    path = os.path.join(DATASETS_DIR, label)
    os.makedirs(path, exist_ok=True)

    with open(os.path.join(path, "logs.json"), "w") as f:
        json.dump(logs, f, indent=2, default=str)
    with open(os.path.join(path, "metrics.json"), "w") as f:
        json.dump(metrics, f, indent=2, default=str)
    with open(os.path.join(path, "ground_truth.json"), "w") as f:
        json.dump(
            {
                "incident_id": label,
                "scenario": scenario,
                "ground_truth": ground_truth,
                "log_count": len(logs),
                "metric_count": len(metrics),
            },
            f,
            indent=2,
        )
    return path


def export_diagnosis(label: str, diagnosis: dict) -> str:
    """Write the AI diagnosis alongside an incident's dataset."""
    path = os.path.join(DATASETS_DIR, label)
    os.makedirs(path, exist_ok=True)
    out = os.path.join(path, "diagnosis.json")
    with open(out, "w") as f:
        json.dump(diagnosis, f, indent=2, default=str)
    return out
