"""AI diagnosis engine (Phase 3).

A single, non-agentic pipeline: take an incident's stored logs + metrics, build a
compact context, ask Gemini for a root-cause analysis, and parse a structured RCA.

Crucially, the ground-truth label is NEVER shown to the model — it only sees the
observability data. That is what makes the resulting prediction a fair benchmark
signal for the Phase 4 evaluation engine.

Output shape:
    {
        "predicted_cause": "redis_outage",   # one of the known cause labels
        "confidence": 0.92,
        "evidence": ["...", "..."],
        "recommended_fix": "..."
    }
"""
import json
import os
from collections import Counter

from .logging_config import get_logger

log = get_logger()

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# The taxonomy the model must classify into (kept in sync with scenarios.SCENARIOS).
KNOWN_CAUSES = [
    "redis_outage",
    "database_deadlock",
    "memory_leak",
    "slow_database",
]

_SYSTEM_INSTRUCTION = (
    "You are a senior site reliability engineer performing root-cause analysis on "
    "a distributed system incident. You are given application logs and resource "
    "metrics. Identify the single most likely root cause. Respond with STRICT JSON "
    "only, no markdown, matching this schema:\n"
    "{\n"
    '  "predicted_cause": one of ' + json.dumps(KNOWN_CAUSES) + ",\n"
    '  "confidence": number between 0 and 1,\n'
    '  "evidence": array of short strings citing specific log lines or metric '
    "patterns that justify the conclusion,\n"
    '  "recommended_fix": short string describing the remediation\n"'
    "}"
)


class DiagnosisError(RuntimeError):
    pass


def build_context(incident: dict) -> str:
    """Render a compact, model-friendly view of an incident's telemetry.

    Sends severity-prioritised log samples and aggregated metric patterns rather
    than the full raw payload, keeping the prompt focused and bounded.
    """
    logs = incident.get("logs", []) or []
    metrics = incident.get("metrics", []) or []

    severities = Counter(l.get("severity", "INFO") for l in logs)

    def sample(severity: str, n: int) -> list:
        msgs = [l.get("message", "") for l in logs if l.get("severity") == severity]
        return msgs[:n]

    # Metric aggregates split by phase so the model can compare before/after.
    def phase_stats(phase: str) -> dict:
        rows = [m for m in metrics if m.get("phase") == phase]
        if not rows:
            return {}
        lat = [m["request_latency"] for m in rows if m.get("request_latency") is not None]
        mem = [m["memory_percent"] for m in rows if m.get("memory_percent") is not None]
        cpu = [m["cpu_percent"] for m in rows if m.get("cpu_percent") is not None]
        agg = lambda xs: (
            {"min": round(min(xs), 2), "max": round(max(xs), 2),
             "avg": round(sum(xs) / len(xs), 2)} if xs else None
        )
        return {
            "samples": len(rows),
            "request_latency_ms": agg(lat),
            "memory_percent": agg(mem),
            "cpu_percent": agg(cpu),
        }

    context = {
        "log_severity_counts": dict(severities),
        "error_samples": sample("ERROR", 8),
        "warning_samples": sample("WARNING", 8),
        "info_samples": sample("INFO", 5),
        "metrics_baseline": phase_stats("baseline"),
        "metrics_failure": phase_stats("failure"),
    }
    return json.dumps(context, indent=2)


def _call_gemini(context: str) -> str:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise DiagnosisError(
            "GEMINI_API_KEY is not set; cannot run AI diagnosis."
        )
    try:
        from google import genai
        from google.genai import types
    except ImportError as err:  # pragma: no cover
        raise DiagnosisError(
            "google-genai is not installed (pip install google-genai)."
        ) from err

    client = genai.Client(api_key=api_key)
    prompt = (
        _SYSTEM_INSTRUCTION
        + "\n\nIncident telemetry:\n"
        + context
        + "\n\nReturn only the JSON object."
    )
    try:
        resp = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.2,
            ),
        )
    except Exception as err:  # network / API errors
        raise DiagnosisError(f"Gemini API call failed: {err}") from err
    return resp.text or ""


def _parse(raw: str) -> dict:
    raw = raw.strip()
    # Be tolerant of accidental code fences.
    if raw.startswith("```"):
        raw = raw.strip("`")
        raw = raw[raw.find("{"): raw.rfind("}") + 1]
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as err:
        raise DiagnosisError(f"could not parse model output as JSON: {err}\n{raw[:500]}")

    cause = str(data.get("predicted_cause", "")).strip()
    if cause not in KNOWN_CAUSES:
        # Keep the raw guess but flag it; evaluation will count it as a miss.
        log.warning("model returned out-of-taxonomy cause: %r", cause)
    try:
        confidence = float(data.get("confidence", 0.0))
    except (TypeError, ValueError):
        confidence = 0.0
    confidence = max(0.0, min(1.0, confidence))

    evidence = data.get("evidence", [])
    if not isinstance(evidence, list):
        evidence = [str(evidence)]

    return {
        "predicted_cause": cause,
        "confidence": round(confidence, 3),
        "evidence": [str(e) for e in evidence],
        "recommended_fix": str(data.get("recommended_fix", "")).strip(),
    }


def _stub_diagnose(incident: dict) -> dict:
    """Deterministic, offline heuristic diagnoser.

    Used when DIAGNOSIS_PROVIDER=stub (e.g. in E2E tests / CI), so the full
    pipeline can run without a Gemini key and produce repeatable results. It maps
    the distinct symptom signatures the scenarios emit to their cause label.
    """
    logs = incident.get("logs", []) or []
    metrics = incident.get("metrics", []) or []
    blob = " ".join((l.get("message") or "").lower() for l in logs)

    def phase_max(phase: str, field: str) -> float:
        vals = [m.get(field) for m in metrics
                if m.get("phase") == phase and m.get(field) is not None]
        return max(vals) if vals else 0.0

    # Each scenario produces a unique phrase; check most-specific first.
    if "deadlock" in blob:
        cause, fix = ("database_deadlock",
                      "Order lock acquisition consistently; add retry on deadlock.")
        evidence = ["log: 'deadlock detected'"]
    elif "connection refused" in blob or "cache unavailable" in blob:
        cause, fix = ("redis_outage",
                      "Restart Redis; add a cache circuit breaker and DB fallback.")
        evidence = ["log: 'Redis connection refused'"]
    elif "oom" in blob or "memory usage high" in blob:
        cause, fix = ("memory_leak",
                      "Find and free the leaking allocation; set memory limits/alerts.")
        evidence = [f"memory_percent peaked at {phase_max('failure','memory_percent')}%",
                    "log: 'OOM warning'"]
    elif "slow database" in blob:
        cause, fix = ("slow_database",
                      "Profile slow queries; add indexes / timeouts.")
        evidence = [f"failure latency up to {phase_max('failure','request_latency')}ms"]
    else:
        cause, fix, evidence = "", "Insufficient signal to determine cause.", []

    confidence = 0.9 if cause else 0.0
    return {
        "predicted_cause": cause,
        "confidence": confidence,
        "evidence": evidence,
        "recommended_fix": fix,
        "model": "stub-heuristic",
    }


def diagnose(incident: dict) -> dict:
    """Run the full diagnosis pipeline for a fetched incident dict.

    Provider is selected by DIAGNOSIS_PROVIDER (default "gemini"). Set it to
    "stub" for an offline, deterministic diagnoser used in tests.
    """
    provider = os.getenv("DIAGNOSIS_PROVIDER", "gemini").lower()
    if provider in ("stub", "mock"):
        log.info("diagnosing %s with stub provider", incident.get("incident_id"))
        return _stub_diagnose(incident)

    context = build_context(incident)
    log.info("diagnosing %s with %s", incident.get("incident_id"), GEMINI_MODEL)
    raw = _call_gemini(context)
    result = _parse(raw)
    result["model"] = GEMINI_MODEL
    return result
