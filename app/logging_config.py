"""JSON logs on stdout. Cloud Logging reads the `severity` field and indexes the rest as jsonPayload."""

import json
import logging
import sys

EXTRA_FIELDS = ("request_id", "method", "path", "status", "latency_ms", "user_id")


class CloudLoggingFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "severity": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
        }
        for key in EXTRA_FIELDS:
            if hasattr(record, key):
                entry[key] = getattr(record, key)
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(entry, ensure_ascii=False, default=str)


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(CloudLoggingFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level.upper())
    # The access-log middleware in app.main replaces uvicorn's plain-text access log
    logging.getLogger("uvicorn.access").disabled = True
