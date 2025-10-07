"""Shared type definitions for the watcher subsystem."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Any
import time


class EventType(Enum):
    """Normalized filesystem event types that the watcher understands."""

    CREATED = auto()
    MODIFIED = auto()
    DELETED = auto()
    MOVED = auto()


@dataclass(slots=True)
class FileSystemEvent:
    """Container describing a single filesystem change event."""

    path: Path
    event_type: EventType
    timestamp: float = field(default_factory=lambda: time.time())
    is_directory: bool = False
    dest_path: Path | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


__all__ = ["EventType", "FileSystemEvent"]
