"""Structured logging utilities for AutoOrganizer."""
from __future__ import annotations

import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

_HOME = Path.home()
_LOG_FORMAT = "%(message)s"
_MAX_BYTES = 10 * 1024 * 1024
_BACKUP_COUNT = 5


def _sanitize(value: str) -> str:
    """Replace home directory with ``~/`` to protect privacy."""

    try:
        path = Path(value)
    except TypeError:
        return value
    try:
        value_str = str(path)
        home_str = str(_HOME)
        if value_str.startswith(home_str):
            remainder = value_str[len(home_str):]
            if remainder.startswith(('/', '\\')):
                remainder = remainder[1:]
            return f"~/{remainder}" if remainder else "~"
        return value_str
    except Exception:  # pragma: no cover - defensive
        return value


def configure_logging(
    log_path: Path | None = None,
    *,
    level: int = logging.INFO,
    max_bytes: int = _MAX_BYTES,
    backup_count: int = _BACKUP_COUNT,
) -> logging.Logger:
    """Configure and return the root logger used throughout the application."""

    logger = logging.getLogger("auto_organizer")
    logger.setLevel(level)
    logger.propagate = False

    if logger.handlers:
        if log_path:
            for handler in list(logger.handlers):
                logger.removeHandler(handler)
                handler.close()
        else:
            for handler in logger.handlers:
                handler.setLevel(level)
            return logger

    if log_path:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        handler: logging.Handler = RotatingFileHandler(
            log_path,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
    else:
        handler = logging.StreamHandler()

    handler.setLevel(level)
    handler.setFormatter(logging.Formatter(_LOG_FORMAT))
    logger.addHandler(handler)
    return logger


def _prepare_payload(data: dict[str, Any]) -> dict[str, Any]:
    sanitized: dict[str, Any] = {}
    for key, value in data.items():
        if isinstance(value, str):
            sanitized[key] = _sanitize(value)
        elif isinstance(value, dict):
            sanitized[key] = _prepare_payload(value)
        elif isinstance(value, (list, tuple)):
            sanitized[key] = [
                _sanitize(item) if isinstance(item, str) else item for item in value
            ]
        else:
            sanitized[key] = value
    return sanitized


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
        "ts": _utcnow_iso(),
        "level": logging.getLevelName(level),
        "action": action,
        "message": _sanitize(message),
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
        payload.update(_prepare_payload(extra))

    logger.log(level, json.dumps(payload, ensure_ascii=False))


def _utcnow_iso() -> str:
    from datetime import datetime

    return datetime.utcnow().isoformat(timespec="milliseconds") + "Z"


__all__ = ["configure_logging", "log_event"]
