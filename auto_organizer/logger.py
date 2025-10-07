"""Structured logging utilities for AutoOrganizer."""
from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

_LOG_FORMAT = "%(message)s"


def configure_logging(log_path: Path | None = None, level: int = logging.INFO) -> logging.Logger:
    """Configure and return the root logger used throughout the application."""

    logger = logging.getLogger("auto_organizer")
    if logger.handlers:
        return logger

    logger.setLevel(level)
    handler: logging.Handler
    if log_path:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        handler = logging.FileHandler(log_path, encoding="utf-8")
    else:
        handler = logging.StreamHandler()

    handler.setFormatter(logging.Formatter(_LOG_FORMAT))
    logger.addHandler(handler)
    return logger


def log_event(
    logger: logging.Logger,
    *,
    level: int,
    action: str,
    message: str,
    task_id: str | None = None,
    file_id: str | None = None,
    bytes_processed: int | None = None,
    duration_ms: float | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    """Emit a structured JSON log entry following the specification."""

    payload: dict[str, Any] = {
        "ts": datetime.utcnow().isoformat(timespec="milliseconds") + "Z",
        "level": logging.getLevelName(level),
        "action": action,
        "message": message,
    }
    if task_id is not None:
        payload["taskId"] = task_id
    if file_id is not None:
        payload["fileId"] = file_id
    if bytes_processed is not None:
        payload["bytes"] = bytes_processed
    if duration_ms is not None:
        payload["ms"] = duration_ms
    if extra:
        payload.update(extra)

    logger.log(level, json.dumps(payload, ensure_ascii=False))
