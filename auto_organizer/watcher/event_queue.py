"""Event queue with debouncing and merge semantics for watcher events."""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict

from .types import EventType, FileSystemEvent


@dataclass(slots=True)
class _QueuedEvent:
    event: FileSystemEvent
    last_seen: float


class EventQueue:
    """Coalesce filesystem events before emitting them downstream."""

    def __init__(
        self,
        emit: Callable[[list[FileSystemEvent]], None],
        *,
        debounce_interval: float = 0.2,
        flush_interval: float = 1.0,
    ) -> None:
        self._emit = emit
        self.debounce_interval = debounce_interval
        self.flush_interval = flush_interval
        self._pending: Dict[Path, _QueuedEvent] = {}
        self._lock = threading.Lock()

    def add(self, event: FileSystemEvent) -> None:
        """Add *event* to the queue, merging it if necessary."""

        now = time.monotonic()
        key = event.path

        with self._lock:
            queued = self._pending.get(key)
            if queued and (now - queued.last_seen) <= self.debounce_interval:
                queued.event = self._merge_events(queued.event, event)
                queued.last_seen = now
            else:
                self._pending[key] = _QueuedEvent(event=event, last_seen=now)

    def flush_due(self, *, force: bool = False) -> None:
        """Flush ready events to the downstream callback."""

        now = time.monotonic()
        ready: list[FileSystemEvent] = []

        with self._lock:
            for key, queued in list(self._pending.items()):
                if force or (now - queued.last_seen) >= self.flush_interval:
                    ready.append(queued.event)
                    del self._pending[key]

        if ready:
            self._emit(ready)

    def clear(self) -> None:
        """Clear internal buffers without emitting events."""

        with self._lock:
            self._pending.clear()

    @staticmethod
    def _merge_events(existing: FileSystemEvent, new: FileSystemEvent) -> FileSystemEvent:
        """Merge two events targeting the same path."""

        if new.event_type is EventType.DELETED:
            merged_type = EventType.DELETED
        elif new.event_type is EventType.MOVED:
            merged_type = EventType.MOVED
        elif existing.event_type is EventType.CREATED and new.event_type is EventType.MODIFIED:
            merged_type = EventType.CREATED
        else:
            merged_type = new.event_type

        existing.event_type = merged_type
        existing.timestamp = new.timestamp
        existing.is_directory = new.is_directory
        if new.dest_path is not None:
            existing.dest_path = new.dest_path
        existing.metadata.update(new.metadata)
        return existing


__all__ = ["EventQueue"]
