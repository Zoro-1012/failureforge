"""Application service — the system under test.

On every /work request it performs a representative unit of work:
  1. write a row to PostgreSQL
  2. read-through the Redis cache (set on miss)
  3. return the result, logging each step as structured JSON

Phase 2 adds control hooks the orchestrator uses to inject the remaining
failures, each producing observable, scenario-specific symptoms in the logs and
metrics:
  POST /config/slow      toggle artificial DB slowness  -> slow_database
  GET  /deadlock         competing transaction          -> database_deadlock
  POST /leak             allocate & retain memory        -> memory_leak
  POST /leak/reset       free leaked memory (recovery)
"""
import os
import time

import psycopg2
import redis
from fastapi import FastAPI, Query

from .cache import cache_get, cache_set
from .db import init_schema, read_item, run_deadlock_txn, slow_query, write_item
from .logging_config import get_logger

log = get_logger()
app = FastAPI(title="FailureForge Application Service")

# --- Runtime-injectable state (driven by the orchestrator) -------------------
STATE = {"slow_seconds": 0.0}
# Retained allocations for the memory_leak scenario.
_LEAK: list[bytearray] = []
_LEAK_WARN_MB = float(os.getenv("LEAK_WARN_MB", "150"))


def _leaked_mb() -> float:
    return round(sum(len(b) for b in _LEAK) / (1024 * 1024), 1)


@app.on_event("startup")
def _startup() -> None:
    init_schema()
    log.info("application service started")


@app.get("/health")
def health():
    return {"status": "ok", "leaked_mb": _leaked_mb(), "slow_seconds": STATE["slow_seconds"]}


@app.get("/work")
def work():
    """Do one unit of DB + cache work and report timing + cache status."""
    started = time.perf_counter()
    cache_status = "miss"
    redis_ok = True

    item_id = write_item("widget")
    cache_key = f"item:{item_id}"

    # Artificial DB slowness (slow_database scenario).
    if STATE["slow_seconds"] > 0:
        log.warning(
            f"slow database query: artificial delay {STATE['slow_seconds']}s",
            extra={"extra": {"slow_seconds": STATE["slow_seconds"]}},
        )
        slow_query(STATE["slow_seconds"])

    # Read-through cache. Failures here are the observable outage symptom.
    try:
        cached = cache_get(cache_key)
        if cached is None:
            row = read_item(item_id)
            cache_set(cache_key, row["name"])
            log.info(
                "cache miss; loaded from db and populated cache",
                extra={"extra": {"key": cache_key}},
            )
        else:
            cache_status = "hit"
            log.info("cache hit", extra={"extra": {"key": cache_key}})
    except (redis.ConnectionError, redis.TimeoutError) as err:
        redis_ok = False
        cache_status = "error"
        # Canonical outage symptom — note the "connection refused" phrasing.
        log.error(
            f"Redis connection refused: cache unavailable ({err})",
            extra={"extra": {"key": cache_key, "error_type": type(err).__name__}},
        )
        read_item(item_id)  # fall back to the database (slower)

    latency_ms = round((time.perf_counter() - started) * 1000, 2)
    log.info(
        "served /work",
        extra={"extra": {"latency_ms": latency_ms, "cache": cache_status}},
    )
    return {
        "item_id": item_id,
        "cache": cache_status,
        "redis_ok": redis_ok,
        "latency_ms": latency_ms,
    }


@app.post("/config/slow")
def config_slow(enabled: bool = Query(True), seconds: float = Query(1.0)):
    """Enable/disable artificial database slowness (slow_database scenario)."""
    STATE["slow_seconds"] = seconds if enabled else 0.0
    log.info(
        f"slow mode {'enabled' if enabled else 'disabled'}",
        extra={"extra": {"slow_seconds": STATE["slow_seconds"]}},
    )
    return {"slow_seconds": STATE["slow_seconds"]}


@app.get("/deadlock")
def deadlock(order: str = Query("ab")):
    """Run a competing transaction. Fire two concurrently with opposite orders
    (ab / ba) to trigger a PostgreSQL deadlock (database_deadlock scenario)."""
    first, second = (1, 2) if order == "ab" else (2, 1)
    started = time.perf_counter()
    try:
        run_deadlock_txn(first, second)
        log.info("transaction committed", extra={"extra": {"order": order}})
        return {"status": "committed", "order": order}
    except psycopg2.errors.DeadlockDetected as err:
        log.error(
            f"deadlock detected: transaction aborted ({str(err).strip()})",
            extra={"extra": {"order": order, "error_type": "DeadlockDetected"}},
        )
        return {"status": "deadlock_detected", "order": order}
    except psycopg2.Error as err:
        log.error(
            f"query failed: {str(err).strip()}",
            extra={"extra": {"order": order, "error_type": type(err).__name__}},
        )
        return {"status": "query_failed", "order": order}
    finally:
        latency_ms = round((time.perf_counter() - started) * 1000, 2)
        log.info("served /deadlock", extra={"extra": {"latency_ms": latency_ms}})


@app.post("/leak")
def leak(mb: int = Query(10), cap_mb: int = Query(180)):
    """Allocate `mb` MB and retain it, simulating a leaking process.

    Stops growing past cap_mb so the container is not OOM-killed during a demo;
    instead it logs an OOM warning once usage crosses the threshold."""
    if _leaked_mb() < cap_mb:
        # Touch the bytes so pages are actually resident (counted by the kernel).
        chunk = bytearray(mb * 1024 * 1024)
        for i in range(0, len(chunk), 4096):
            chunk[i] = 1
        _LEAK.append(chunk)

    leaked = _leaked_mb()
    if leaked >= _LEAK_WARN_MB:
        log.warning(
            f"OOM warning: memory usage high ({leaked} MB retained)",
            extra={"extra": {"leaked_mb": leaked}},
        )
    else:
        log.info("memory allocated", extra={"extra": {"leaked_mb": leaked}})
    return {"leaked_mb": leaked}


@app.post("/leak/reset")
def leak_reset():
    """Free all retained memory (memory_leak recovery)."""
    _LEAK.clear()
    log.info("memory released", extra={"extra": {"leaked_mb": _leaked_mb()}})
    return {"leaked_mb": _leaked_mb()}
