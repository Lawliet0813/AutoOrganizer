"""Realtime filesystem watcher with macOS FSEvents integration."""
from __future__ import annotations

import fnmatch
import logging
import sys
import threading
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from queue import Empty, Queue
from typing import Any, Callable, Sequence

try:  # pragma: no cover - optional dependency
    from fsevents import Observer, Stream  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    Observer = None  # type: ignore[assignment]
    Stream = None  # type: ignore[assignment]

from .logger import configure_logging, log_event

LOGGER_NAME = "auto_organizer.realtime"


class EventType(Enum):
    """Known filesystem event types."""

    CREATED = auto()
    MODIFIED = auto()
    DELETED = auto()
    MOVED = auto()


@dataclass(slots=True)
class FileSystemEvent:
    """Normalized filesystem event payload."""

    path: Path
    event_type: EventType
    timestamp: float = field(default_factory=lambda: time.time())
    is_directory: bool = False
    dest_path: Path | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class _WatcherBackend:
    """Base protocol for realtime watcher backends."""

    def start(self) -> None:  # pragma: no cover - exercised in integration
        raise NotImplementedError

    def stop(self) -> None:  # pragma: no cover - exercised in integration
        raise NotImplementedError


class _FSEventsBackend(_WatcherBackend):  # pragma: no cover - macOS only
    """macOS FSEvents backend."""

    def __init__(self, watcher: "RealtimeWatcher") -> None:
        if Observer is None or Stream is None:
            raise RuntimeError("fsevents package is not available")

        self._watcher = watcher
        self._observer = Observer()
        self._streams: list[Any] = []

    def start(self) -> None:
        for path in self._watcher.paths:
            stream = Stream(
                self._handle_event,
                str(path),
                file_events=True,
            )
            self._streams.append(stream)
            self._observer.schedule(stream)
        self._observer.start()

    def stop(self) -> None:
        self._observer.stop()
        self._observer.join()
        self._streams.clear()

    def _handle_event(self, event: Any) -> None:
        event_type = self._map_event_type(event)
        if event_type is None:
            return
        dest_path = Path(event.dest) if getattr(event, "dest", None) else None
        filesystem_event = FileSystemEvent(
            path=Path(event.name),
            event_type=event_type,
            timestamp=time.time(),
            is_directory=bool(getattr(event, "isDirectory", False)),
            dest_path=dest_path,
        )
        self._watcher.publish(filesystem_event)

    @staticmethod
    def _map_event_type(event: Any) -> EventType | None:
        flag = getattr(event, "mask", 0)
        # These constants mirror fsevents module exports.
        created_mask = getattr(event, "ITEM_CREATED", 0) or getattr(event, "ITEM_IS_FILE", 0)
        removed_mask = getattr(event, "ITEM_REMOVED", 0)
        renamed_mask = getattr(event, "ITEM_RENAMED", 0)
        modified_mask = getattr(event, "ITEM_MODIFIED", 0)

        if flag & renamed_mask:
            return EventType.MOVED
        if flag & removed_mask:
            return EventType.DELETED
        if flag & created_mask:
            return EventType.CREATED
        if flag & modified_mask:
            return EventType.MODIFIED
        return None


class RealtimeWatcher:
    """Aggregates realtime filesystem events with debouncing and batching."""

    def __init__(
        self,
        paths: Sequence[str | Path],
        callback: Callable[[list[FileSystemEvent]], None],
        *,
        debounce_interval: float = 0.2,
        batch_interval: float = 1.0,
        blacklist_patterns: Sequence[str] | None = None,
        backend_factory: Callable[["RealtimeWatcher"], _WatcherBackend | None] | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        if not paths:
            raise ValueError("At least one path must be provided for realtime watching")

        self.paths = [Path(path).expanduser() for path in paths]
        self.callback = callback
        self.debounce_interval = debounce_interval
        self.batch_interval = batch_interval
        self.blacklist_patterns = list(blacklist_patterns or [])
        self._backend_factory = backend_factory or self._default_backend_factory
        self._queue: Queue[FileSystemEvent | object] = Queue()
        self._stop_event = threading.Event()
        self._worker: threading.Thread | None = None
        self._backend: _WatcherBackend | None = None
        self._lock = threading.Lock()

        self.logger = logger or logging.getLogger(LOGGER_NAME)
        if not self.logger.handlers:
            configure_logging()

    def start(self) -> None:
        with self._lock:
            if self._worker and self._worker.is_alive():
                return

            self._stop_event.clear()
            self._worker = threading.Thread(target=self._run, name="RealtimeWatcher", daemon=True)
            self._worker.start()

            try:
                self._backend = self._backend_factory(self)
            except Exception as exc:  # pragma: no cover - defensive
                log_event(
                    self.logger,
                    level=logging.WARNING,
                    action="watcher.backend_error",
                    message="Failed to initialize realtime backend",
                    extra={"error": repr(exc)},
                )
                self._backend = None

            if self._backend:
                self._backend.start()
            else:
                log_event(
                    self.logger,
                    level=logging.INFO,
                    action="watcher.backend_disabled",
                    message="Realtime backend is not available; watcher will only process manual events",
                )

    def stop(self) -> None:
        with self._lock:
            self._stop_event.set()
            self._queue.put(_Sentinel)
            if self._backend:
                try:
                    self._backend.stop()
                finally:
                    self._backend = None

            worker = self._worker
            if worker and worker.is_alive():
                worker.join()
            self._worker = None

    def publish(self, event: FileSystemEvent) -> None:
        """Submit a filesystem *event* for aggregation."""

        self._queue.put(event)

    def enqueue(
        self,
        path: str | Path,
        event_type: EventType,
        *,
        is_directory: bool = False,
        dest_path: str | Path | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Helper for tests and manual injection."""

        filesystem_event = FileSystemEvent(
            path=Path(path),
            event_type=event_type,
            is_directory=is_directory,
            dest_path=Path(dest_path) if dest_path else None,
            metadata=metadata or {},
        )
        self.publish(filesystem_event)

    def _run(self) -> None:
        pending: dict[Path, FileSystemEvent] = {}
        last_seen: dict[Path, float] = {}
        last_flush = time.monotonic()

        while not self._stop_event.is_set():
            timeout = max(self.batch_interval / 5, 0.05)
            try:
                item = self._queue.get(timeout=timeout)
            except Empty:
                item = None

            now = time.monotonic()

            if item is _Sentinel:
                break
            if isinstance(item, FileSystemEvent):
                if self._is_blacklisted(item.path):
                    continue
                last_time = last_seen.get(item.path)
                if last_time is not None and (now - last_time) <= self.debounce_interval:
                    existing = pending[item.path]
                    existing.event_type = self._coalesce(existing.event_type, item.event_type)
                    existing.timestamp = item.timestamp
                    existing.is_directory = item.is_directory
                    existing.dest_path = item.dest_path or existing.dest_path
                    existing.metadata.update(item.metadata)
                else:
                    pending[item.path] = item
                last_seen[item.path] = now

            if pending and (now - last_flush) >= self.batch_interval:
                self._emit(list(pending.values()))
                pending.clear()
                last_seen.clear()
                last_flush = now

        if pending:
            self._emit(list(pending.values()))

    def _emit(self, events: list[FileSystemEvent]) -> None:
        try:
            self.callback(events)
        except Exception as exc:  # pragma: no cover - defensive
            log_event(
                self.logger,
                level=logging.ERROR,
                action="watcher.callback_error",
                message="Realtime callback raised an exception",
                extra={"error": repr(exc)},
            )

    def _is_blacklisted(self, path: Path) -> bool:
        if not self.blacklist_patterns:
            return False
        for pattern in self.blacklist_patterns:
            if fnmatch.fnmatch(path.name, pattern) or fnmatch.fnmatch(str(path), pattern):
                return True
        return False

    @staticmethod
    def _coalesce(existing: EventType, new: EventType) -> EventType:
        if new is EventType.DELETED:
            return EventType.DELETED
        if new is EventType.MOVED:
            return EventType.MOVED
        if existing is EventType.CREATED and new is EventType.MODIFIED:
            return EventType.CREATED
        return new

    @staticmethod
    def _default_backend_factory(watcher: "RealtimeWatcher") -> _WatcherBackend | None:
        if sys.platform == "darwin" and Observer is not None and Stream is not None:
            try:
                return _FSEventsBackend(watcher)
            except Exception:  # pragma: no cover - optional
                return None
        return None


_Sentinel = object()


__all__ = [
    "EventType",
    "FileSystemEvent",
    "RealtimeWatcher",
]

