"""Structured JSON logging for the orchestrator (same shape as the app)."""
import json
import logging
import sys
from datetime import datetime, timezone

SERVICE_NAME = "orchestrator"


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return json.dumps(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "service": SERVICE_NAME,
                "severity": record.levelname,
                "message": record.getMessage(),
            }
        )


def get_logger() -> logging.Logger:
    logger = logging.getLogger(SERVICE_NAME)
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
    logger.propagate = False
    return logger
