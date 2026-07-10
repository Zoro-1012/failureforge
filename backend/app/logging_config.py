"""Structured JSON logging for the application service.

Every log line is a single JSON object with the canonical telemetry fields:
    timestamp, service, severity, message

Logs are written to stdout (so `docker compose logs` works) and appended to a
shared log file under LOG_DIR so the orchestrator can collect them when building
an incident.
"""
import json
import logging
import os
import sys
from datetime import datetime, timezone

SERVICE_NAME = os.getenv("SERVICE_NAME", "app")
LOG_DIR = os.getenv("LOG_DIR", "/var/log/failureforge")
LOG_FILE = os.path.join(LOG_DIR, f"{SERVICE_NAME}.log")


class JsonFormatter(logging.Formatter):
    """Render log records as the canonical telemetry JSON shape."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "service": SERVICE_NAME,
            "severity": record.levelname,
            "message": record.getMessage(),
        }
        # Allow callers to attach structured extras via logger.x(..., extra={"extra": {...}})
        extra = getattr(record, "extra", None)
        if isinstance(extra, dict):
            payload.update(extra)
        return json.dumps(payload)


def get_logger() -> logging.Logger:
    logger = logging.getLogger(SERVICE_NAME)
    if logger.handlers:  # already configured
        return logger

    logger.setLevel(logging.INFO)
    formatter = JsonFormatter()

    stream = logging.StreamHandler(sys.stdout)
    stream.setFormatter(formatter)
    logger.addHandler(stream)

    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        file_handler = logging.FileHandler(LOG_FILE)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except OSError:
        # If the log volume isn't writable, stdout logging still works.
        logger.warning("could not open log file at %s", LOG_FILE)

    logger.propagate = False
    return logger
