"""Telemetry collection: container metrics + request latency.

Metrics are sampled from Docker stats for the application container and combined
with the latency of a probe request to the app's /work endpoint. Each sample has
the canonical metric fields:
    timestamp, cpu_percent, memory_percent, request_latency
plus a `phase` tag (baseline / failure) so symptoms are easy to compare.
"""
import time
from datetime import datetime, timezone

import httpx

from .docker_control import APP_CONTAINER, get_container

APP_URL = "http://app:8001"


def _cpu_percent(stats: dict) -> float:
    """Compute CPU % from two cumulative Docker stats snapshots."""
    try:
        cpu = stats["cpu_stats"]
        pre = stats["precpu_stats"]
        cpu_delta = cpu["cpu_usage"]["total_usage"] - pre["cpu_usage"]["total_usage"]
        system_delta = cpu["system_cpu_usage"] - pre["system_cpu_usage"]
        online = cpu.get("online_cpus") or len(
            cpu["cpu_usage"].get("percpu_usage") or [1]
        )
        if system_delta > 0 and cpu_delta > 0:
            return round((cpu_delta / system_delta) * online * 100.0, 2)
    except (KeyError, TypeError, ZeroDivisionError):
        pass
    return 0.0


def _memory_percent(stats: dict) -> float:
    try:
        mem = stats["memory_stats"]
        usage = mem["usage"]
        limit = mem["limit"]
        if limit > 0:
            return round((usage / limit) * 100.0, 2)
    except (KeyError, TypeError, ZeroDivisionError):
        pass
    return 0.0


def probe_latency(client: httpx.Client, path: str = "/work") -> tuple[float, bool]:
    """Hit an endpoint and return (latency_ms, ok). Generates load + measures it."""
    started = time.perf_counter()
    try:
        resp = client.get(f"{APP_URL}{path}", timeout=30.0)
        latency = round((time.perf_counter() - started) * 1000, 2)
        return latency, resp.status_code == 200
    except httpx.HTTPError:
        latency = round((time.perf_counter() - started) * 1000, 2)
        return latency, False


def sample(client: httpx.Client, phase: str, path: str = "/work") -> dict:
    """Take one combined telemetry sample, probing `path` for latency."""
    latency, ok = probe_latency(client, path)
    cpu = mem = 0.0
    try:
        stats = get_container(APP_CONTAINER).stats(stream=False)
        cpu = _cpu_percent(stats)
        mem = _memory_percent(stats)
    except Exception:  # stats best-effort; latency is the key signal
        pass
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "phase": phase,
        "cpu_percent": cpu,
        "memory_percent": mem,
        "request_latency": latency,
        "request_ok": ok,
    }
