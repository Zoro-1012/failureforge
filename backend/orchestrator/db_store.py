"""Persistent telemetry storage in PostgreSQL — the system of record.

Phase 2 promotes the orchestrator's storage from flat files to a relational
store. Every incident, log line, and metric sample is persisted in PostgreSQL so
incidents are queryable and survive restarts. The flat-file benchmark dataset is
still exported alongside (see storage.py) because that portable dataset is one of
the project's core deliverables.

Schema:
    incidents(id, label, scenario, ground_truth, started_at, log_count,
              metric_count, summary)
    logs(id, incident_id, ts, service, severity, message)
    metrics(id, incident_id, ts, phase, cpu_percent, memory_percent,
            request_latency, request_ok)
"""
import json
import os
import time

import psycopg2
from psycopg2.extras import RealDictCursor, execute_values

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://forge:forge@postgres:5432/failureforge"
)


def connect(retries: int = 10, delay: float = 1.5):
    last_err = None
    for _ in range(retries):
        try:
            return psycopg2.connect(DATABASE_URL)
        except psycopg2.OperationalError as err:
            last_err = err
            time.sleep(delay)
    raise last_err


def init_schema() -> None:
    conn = connect()
    try:
        with conn, conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS incidents (
                    id           SERIAL PRIMARY KEY,
                    label        TEXT UNIQUE,
                    scenario     TEXT NOT NULL,
                    ground_truth TEXT NOT NULL,
                    started_at   TIMESTAMPTZ DEFAULT now(),
                    log_count    INTEGER DEFAULT 0,
                    metric_count INTEGER DEFAULT 0,
                    summary      JSONB
                );
                CREATE TABLE IF NOT EXISTS logs (
                    id          SERIAL PRIMARY KEY,
                    incident_id INTEGER REFERENCES incidents(id) ON DELETE CASCADE,
                    ts          TEXT,
                    service     TEXT,
                    severity    TEXT,
                    message     TEXT
                );
                CREATE TABLE IF NOT EXISTS metrics (
                    id              SERIAL PRIMARY KEY,
                    incident_id     INTEGER REFERENCES incidents(id) ON DELETE CASCADE,
                    ts              TEXT,
                    phase           TEXT,
                    cpu_percent     REAL,
                    memory_percent  REAL,
                    request_latency REAL,
                    request_ok      BOOLEAN
                );
                CREATE TABLE IF NOT EXISTS diagnoses (
                    id              SERIAL PRIMARY KEY,
                    incident_id     INTEGER REFERENCES incidents(id) ON DELETE CASCADE,
                    predicted_cause TEXT,
                    confidence      REAL,
                    evidence        JSONB,
                    recommended_fix TEXT,
                    model           TEXT,
                    created_at      TIMESTAMPTZ DEFAULT now()
                );
                """
            )
    finally:
        conn.close()


def create_incident(scenario: str, ground_truth: str, logs: list,
                    metrics: list, summary: dict) -> dict:
    """Persist an incident with its logs and metrics; return the metadata dict."""
    conn = connect()
    try:
        with conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO incidents (scenario, ground_truth, log_count,
                                       metric_count, summary)
                VALUES (%s, %s, %s, %s, %s) RETURNING id
                """,
                (scenario, ground_truth, len(logs), len(metrics),
                 json.dumps(summary)),
            )
            incident_id = cur.fetchone()[0]
            label = f"incident_{incident_id:03d}"
            cur.execute(
                "UPDATE incidents SET label = %s WHERE id = %s", (label, incident_id)
            )

            if logs:
                execute_values(
                    cur,
                    "INSERT INTO logs (incident_id, ts, service, severity, message)"
                    " VALUES %s",
                    [
                        (incident_id, l.get("timestamp"), l.get("service"),
                         l.get("severity"), l.get("message"))
                        for l in logs
                    ],
                )
            if metrics:
                execute_values(
                    cur,
                    "INSERT INTO metrics (incident_id, ts, phase, cpu_percent,"
                    " memory_percent, request_latency, request_ok) VALUES %s",
                    [
                        (incident_id, m.get("timestamp"), m.get("phase"),
                         m.get("cpu_percent"), m.get("memory_percent"),
                         m.get("request_latency"), m.get("request_ok"))
                        for m in metrics
                    ],
                )
    finally:
        conn.close()

    return {
        "incident_id": label,
        "scenario": scenario,
        "ground_truth": ground_truth,
        "log_count": len(logs),
        "metric_count": len(metrics),
        "summary": summary,
    }


def _incident_pk(cur, label: str):
    cur.execute("SELECT id FROM incidents WHERE label = %s", (label,))
    row = cur.fetchone()
    return row[0] if row else None


def save_diagnosis(label: str, result: dict) -> dict | None:
    """Persist an AI diagnosis for an incident. Returns None if incident missing."""
    conn = connect()
    try:
        with conn, conn.cursor() as cur:
            incident_pk = _incident_pk(cur, label)
            if incident_pk is None:
                return None
            cur.execute(
                """
                INSERT INTO diagnoses (incident_id, predicted_cause, confidence,
                                       evidence, recommended_fix, model)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    incident_pk,
                    result.get("predicted_cause"),
                    result.get("confidence"),
                    json.dumps(result.get("evidence", [])),
                    result.get("recommended_fix"),
                    result.get("model"),
                ),
            )
    finally:
        conn.close()
    return {"incident_id": label, **result}


def get_latest_diagnosis(label: str) -> dict | None:
    conn = connect()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            incident_pk = _incident_pk(cur, label)
            if incident_pk is None:
                return None
            cur.execute(
                "SELECT predicted_cause, confidence, evidence, recommended_fix,"
                " model, created_at FROM diagnoses WHERE incident_id = %s"
                " ORDER BY id DESC LIMIT 1", (incident_pk,)
            )
            row = cur.fetchone()
    finally:
        conn.close()
    if row and row.get("created_at") is not None:
        row["created_at"] = row["created_at"].isoformat()
    return row


def get_eval_pairs() -> list:
    """Return every incident with its latest predicted cause (if diagnosed).

    Each row: {incident_id, ground_truth, predicted_cause, confidence}.
    predicted_cause/confidence are None for incidents not yet diagnosed.
    """
    conn = connect()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT i.label AS incident_id,
                       i.ground_truth,
                       d.predicted_cause,
                       d.confidence
                FROM incidents i
                LEFT JOIN LATERAL (
                    SELECT predicted_cause, confidence
                    FROM diagnoses dd
                    WHERE dd.incident_id = i.id
                    ORDER BY dd.id DESC
                    LIMIT 1
                ) d ON TRUE
                ORDER BY i.id
                """
            )
            return cur.fetchall()
    finally:
        conn.close()


def list_incidents() -> list:
    conn = connect()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT label AS incident_id, scenario, ground_truth, started_at,"
                " log_count, metric_count, summary FROM incidents ORDER BY id"
            )
            rows = cur.fetchall()
    finally:
        conn.close()
    for r in rows:
        if r.get("started_at") is not None:
            r["started_at"] = r["started_at"].isoformat()
    return rows


def get_incident(label: str) -> dict | None:
    conn = connect()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT id, label, scenario, ground_truth, started_at, log_count,"
                " metric_count, summary FROM incidents WHERE label = %s", (label,)
            )
            meta = cur.fetchone()
            if meta is None:
                return None
            incident_pk = meta["id"]
            if meta.get("started_at") is not None:
                meta["started_at"] = meta["started_at"].isoformat()

            cur.execute(
                "SELECT ts AS timestamp, service, severity, message FROM logs"
                " WHERE incident_id = %s ORDER BY id", (incident_pk,)
            )
            logs = cur.fetchall()
            cur.execute(
                "SELECT ts AS timestamp, phase, cpu_percent, memory_percent,"
                " request_latency, request_ok FROM metrics WHERE incident_id = %s"
                " ORDER BY id", (incident_pk,)
            )
            metrics = cur.fetchall()
    finally:
        conn.close()

    return {
        "incident_id": label,
        "ground_truth": {
            "incident_id": label,
            "scenario": meta["scenario"],
            "ground_truth": meta["ground_truth"],
            "log_count": meta["log_count"],
            "metric_count": meta["metric_count"],
        },
        "summary": meta["summary"],
        "logs": logs,
        "metrics": metrics,
        "diagnosis": get_latest_diagnosis(label),
    }
