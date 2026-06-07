"""Structured logging configuration for BioOrchestrator.

Call setup_logging() once at application startup (in src/app.py).

- Development (APP_ENV != "production"): human-readable format to stdout
- Production (APP_ENV=production): JSON format for log aggregation (Datadog, CloudWatch, etc.)
- Optional Sentry integration via SENTRY_DSN env var (no-op if not set)
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone


def setup_logging() -> None:
    """Configure root logger and optionally initialize Sentry."""
    env = os.getenv("APP_ENV", "development")
    level = logging.DEBUG if env == "development" else logging.INFO

    if env == "production":
        handler = logging.StreamHandler()
        handler.setFormatter(_JsonFormatter())
    else:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)-8s %(name)s: %(message)s")
        )

    root = logging.getLogger()
    root.setLevel(level)
    # Avoid duplicate handlers if called multiple times (Streamlit reruns)
    if not root.handlers:
        root.addHandler(handler)

    # Suppress noisy libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("anthropic").setLevel(logging.WARNING)

    # Optional Sentry integration
    sentry_dsn = os.getenv("SENTRY_DSN")
    if sentry_dsn:
        try:
            import sentry_sdk
            sentry_sdk.init(
                dsn=sentry_dsn,
                traces_sample_rate=0.1,
                environment=env,
            )
            logging.getLogger(__name__).info("Sentry initialized (env=%s)", env)
        except ImportError:
            logging.getLogger(__name__).warning(
                "SENTRY_DSN is set but sentry-sdk is not installed. "
                "Run: pip install 'sentry-sdk[streamlit]'"
            )


class _JsonFormatter(logging.Formatter):
    """JSON log formatter for production log aggregation."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "time": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "module": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload)
