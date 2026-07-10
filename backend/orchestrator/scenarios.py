"""Failure scenario definitions.

Phase 2 implements all four scenarios behind one generic orchestration loop:

    baseline (observe healthy) -> inject+observe (drive symptoms) -> recover
    -> collect logs -> persist (PostgreSQL + dataset export)

Each scenario provides an `inject` callable that takes the orchestration context
and appends failure-phase telemetry samples while producing scenario-specific
symptoms in the application logs.
"""
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import httpx

from . import db_store, docker_control, storage, telemetry
from .logging_config import get_logger

log = get_logger()

APP_LOG_FILE = os.getenv("APP_LOG_FILE", "/var/log/failureforge/app.log")
APP_URL = telemetry.APP_URL

# scenario name -> ground-truth label
SCENARIOS = {
    "redis_outage": "redis_outage",
    "database_deadlock": "database_deadlock",
    "memory_leak": "memory_leak",
    "slow_database": "slow_database",
}


# --- helpers -----------------------------------------------------------------
def _read_app_logs(since_iso: str) -> list:
    logs = []
    if not os.path.isfile(APP_LOG_FILE):
        return logs
    with open(APP_LOG_FILE) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if entry.get("timestamp", "") >= since_iso:
                logs.append(entry)
    return logs


def _baseline(client: httpx.Client, metrics: list, n: int = 5) -> None:
    log.info("baseline phase (%d samples)", n)
    for _ in range(n):
        metrics.append(telemetry.sample(client, phase="baseline"))
        time.sleep(1.0)


def _summarize(metrics: list, logs: list) -> dict:
    base = [m["request_latency"] for m in metrics if m["phase"] == "baseline"]
    fail = [m["request_latency"] for m in metrics if m["phase"] == "failure"]
    base_mem = [m["memory_percent"] for m in metrics if m["phase"] == "baseline"]
    fail_mem = [m["memory_percent"] for m in metrics if m["phase"] == "failure"]
    errors = [l for l in logs if l.get("severity") == "ERROR"]
    warnings = [l for l in logs if l.get("severity") == "WARNING"]
    avg = lambda xs: round(sum(xs) / len(xs), 2) if xs else None
    return {
        "avg_baseline_latency_ms": avg(base),
        "avg_failure_latency_ms": avg(fail),
        "max_baseline_memory_percent": max(base_mem) if base_mem else None,
        "max_failure_memory_percent": max(fail_mem) if fail_mem else None,
        "error_log_count": len(errors),
        "warning_log_count": len(warnings),
    }


# --- per-scenario inject functions -------------------------------------------
def _inject_redis_outage(client: httpx.Client, metrics: list, samples: int = 8):
    log.info("injecting failure: stopping %s", docker_control.REDIS_CONTAINER)
    docker_control.stop_container(docker_control.REDIS_CONTAINER)
    try:
        for _ in range(samples):
            metrics.append(telemetry.sample(client, phase="failure"))
            time.sleep(1.0)
    finally:
        log.info("recovering: starting %s", docker_control.REDIS_CONTAINER)
        docker_control.start_container(docker_control.REDIS_CONTAINER)


def _inject_database_deadlock(client: httpx.Client, metrics: list, rounds: int = 6):
    log.info("injecting failure: competing transactions")

    def hit(order: str):
        try:
            client.get(f"{APP_URL}/deadlock", params={"order": order}, timeout=30.0)
        except httpx.HTTPError:
            pass

    with ThreadPoolExecutor(max_workers=2) as pool:
        for _ in range(rounds):
            # Fire opposite lock orders concurrently to create a deadlock cycle.
            f1 = pool.submit(hit, "ab")
            f2 = pool.submit(hit, "ba")
            f1.result()
            f2.result()
            metrics.append(telemetry.sample(client, phase="failure"))
    # No container action needed; nothing to recover.


def _inject_memory_leak(client: httpx.Client, metrics: list, steps: int = 12):
    log.info("injecting failure: continuous memory allocation")
    try:
        for _ in range(steps):
            try:
                client.post(f"{APP_URL}/leak", params={"mb": 15}, timeout=15.0)
            except httpx.HTTPError:
                pass
            metrics.append(telemetry.sample(client, phase="failure"))
            time.sleep(0.8)
    finally:
        log.info("recovering: releasing leaked memory")
        try:
            client.post(f"{APP_URL}/leak/reset", timeout=15.0)
        except httpx.HTTPError:
            pass


def _inject_slow_database(client: httpx.Client, metrics: list, samples: int = 8):
    log.info("injecting failure: enabling artificial query delays")
    try:
        client.post(f"{APP_URL}/config/slow",
                    params={"enabled": True, "seconds": 1.0}, timeout=15.0)
        for _ in range(samples):
            metrics.append(telemetry.sample(client, phase="failure"))
            time.sleep(0.5)
    finally:
        log.info("recovering: disabling artificial query delays")
        try:
            client.post(f"{APP_URL}/config/slow",
                        params={"enabled": False}, timeout=15.0)
        except httpx.HTTPError:
            pass


_INJECTORS = {
    "redis_outage": _inject_redis_outage,
    "database_deadlock": _inject_database_deadlock,
    "memory_leak": _inject_memory_leak,
    "slow_database": _inject_slow_database,
}


# --- generic runner ----------------------------------------------------------
def run_scenario(name: str) -> dict:
    if name not in SCENARIOS:
        raise ValueError(f"unknown scenario '{name}'")

    started_iso = datetime.now(timezone.utc).isoformat()
    metrics: list = []
    log.info("%s: starting scenario", name)

    with httpx.Client() as client:
        _baseline(client, metrics)
        _INJECTORS[name](client, metrics)

    logs = _read_app_logs(started_iso)
    summary = _summarize(metrics, logs)

    # Persist to PostgreSQL (system of record) and export the benchmark dataset.
    incident = db_store.create_incident(
        scenario=name,
        ground_truth=SCENARIOS[name],
        logs=logs,
        metrics=metrics,
        summary=summary,
    )
    storage.export_incident(
        label=incident["incident_id"],
        scenario=name,
        ground_truth=SCENARIOS[name],
        logs=logs,
        metrics=metrics,
    )
    log.info("%s: persisted %s", name, incident["incident_id"])
    return incident


# Backwards-compatible alias used by earlier code / tests.
def run_redis_outage() -> dict:
    return run_scenario("redis_outage")
