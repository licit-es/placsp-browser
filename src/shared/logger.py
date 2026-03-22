"""Centralized logging setup for the ETL pipeline.

Every module uses ``from common.logger import get_logger`` followed by
``logger = get_logger(__name__)`` at module level.
"""

from __future__ import annotations

import logging
import os
import sys
from datetime import UTC, datetime

_LOG_FORMAT = (
    "%(asctime)s [%(levelname)s] %(name)s (%(filename)s:%(lineno)d): %(message)s"
)

_NOISY_LOGGERS = ("httpx", "asyncpg", "httpcore", "hpack", "httptools")

_state = {"initialized": False}


class _DebugOnlyFilter(logging.Filter):
    """Pass only DEBUG records."""

    def filter(self, record: logging.LogRecord) -> bool:
        return record.levelno == logging.DEBUG


class _InfoWarningFilter(logging.Filter):
    """Pass only INFO and WARNING records."""

    def filter(self, record: logging.LogRecord) -> bool:
        return record.levelno in (logging.INFO, logging.WARNING)


class _ErrorCriticalFilter(logging.Filter):
    """Pass only ERROR and CRITICAL records."""

    def filter(self, record: logging.LogRecord) -> bool:
        return record.levelno >= logging.ERROR


def _setup() -> None:
    """One-time root logger configuration.  Idempotent."""
    if _state["initialized"]:
        return
    _state["initialized"] = True

    level_name = os.environ.get("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    root = logging.getLogger()
    root.setLevel(level)

    formatter = logging.Formatter(_LOG_FORMAT)

    # Console -> stdout (Lambda captures stdout to CloudWatch)
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(level)
    console.setFormatter(formatter)
    root.addHandler(console)

    # Suppress third-party noise
    for name in _NOISY_LOGGERS:
        logging.getLogger(name).setLevel(logging.WARNING)

    # File logging -- CLI seeding only
    if os.environ.get("ENABLE_FILE_LOGGING", "").lower() in ("true", "1"):
        _add_file_handlers(root, formatter)


def _add_file_handlers(
    root: logging.Logger,
    formatter: logging.Formatter,
) -> None:
    timestamp = datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%SZ")
    log_dir = os.path.join("logs", timestamp)
    os.makedirs(log_dir, exist_ok=True)

    # debug.log -- DEBUG only
    debug_handler = logging.FileHandler(os.path.join(log_dir, "debug.log"))
    debug_handler.setLevel(logging.DEBUG)
    debug_handler.addFilter(_DebugOnlyFilter())
    debug_handler.setFormatter(formatter)
    root.addHandler(debug_handler)

    # info_warning.log -- INFO + WARNING
    info_handler = logging.FileHandler(os.path.join(log_dir, "info_warning.log"))
    info_handler.setLevel(logging.DEBUG)
    info_handler.addFilter(_InfoWarningFilter())
    info_handler.setFormatter(formatter)
    root.addHandler(info_handler)

    # error.log -- ERROR + CRITICAL
    error_handler = logging.FileHandler(os.path.join(log_dir, "error.log"))
    error_handler.setLevel(logging.ERROR)
    error_handler.addFilter(_ErrorCriticalFilter())
    error_handler.setFormatter(formatter)
    root.addHandler(error_handler)

    # When file logging is on, root must capture DEBUG for the debug file
    root.setLevel(logging.DEBUG)


def get_logger(name: str) -> logging.Logger:
    """Return a named logger, bootstrapping the root config on first call."""
    _setup()
    return logging.getLogger(name)
