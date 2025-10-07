"""Realtime filesystem watcher with macOS FSEvents integration."""
from __future__ import annotations

import fnmatch
import logging
import os
import sys
import threading
import time
from pathlib import Path
from queue import Empty, Queue
from typing import Any, Callable, Sequence

try:  # pragma: no cover - optional dependency
    from fsevents import Observer, Stream  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    Observer = None  # type: ignore[assignment]
    Stream = None  # type: ignore[assignment]

from .logger import configure_logging, log_event
from .watcher.event_queue import EventQueue
from .watcher.types import EventType, FileSystemEvent

LOGGER_NAME = "auto_organizer.realtime"


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
        polling_interval: float = 2.0,
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
        self.polling_interval = polling_interval

        self._event_queue = EventQueue(
            self._emit,
            debounce_interval=self.debounce_interval,
            flush_interval=self.batch_interval,
        )

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
        while not self._stop_event.is_set():
            timeout = max(self.batch_interval / 5, 0.05)
            try:
                item = self._queue.get(timeout=timeout)
            except Empty:
                self._event_queue.flush_due()
                continue

            if item is _Sentinel:
                break
            if isinstance(item, FileSystemEvent):
                if self._is_blacklisted(item.path):
                    continue
                self._event_queue.add(item)
                self._event_queue.flush_due()

        self._event_queue.flush_due(force=True)

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
    def _default_backend_factory(watcher: "RealtimeWatcher") -> _WatcherBackend | None:
        if sys.platform == "darwin" and Observer is not None and Stream is not None:
            try:
                return _FSEventsBackend(watcher)
            except Exception:  # pragma: no cover - optional
                return None
        return _PollingBackend(watcher)


class _PollingBackend(_WatcherBackend):
    """Simple polling backend used when FSEvents is unavailable."""

    def __init__(self, watcher: "RealtimeWatcher") -> None:
        self._watcher = watcher
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._snapshot: dict[Path, tuple[float, int]] = {}

    def start(self) -> None:
        self._snapshot = self._build_snapshot()
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, name="WatcherPolling", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        thread = self._thread
        if thread and thread.is_alive():
            thread.join()
        self._thread = None

    def _run(self) -> None:
        interval = max(self._watcher.polling_interval, 0.5)
        while not self._stop_event.wait(interval):
            self._scan()

    def _scan(self) -> None:
        current = self._build_snapshot()
        previous = self._snapshot

        previous_paths = set(previous)
        current_paths = set(current)

        for path in current_paths - previous_paths:
            self._watcher.publish(
                FileSystemEvent(path=path, event_type=EventType.CREATED, is_directory=path.is_dir())
            )

        for path in previous_paths - current_paths:
            self._watcher.publish(
                FileSystemEvent(path=path, event_type=EventType.DELETED, is_directory=False)
            )

        for path in previous_paths & current_paths:
            old_mtime, old_size = previous[path]
            new_mtime, new_size = current[path]
            if old_mtime != new_mtime or old_size != new_size:
                self._watcher.publish(
                    FileSystemEvent(path=path, event_type=EventType.MODIFIED, is_directory=path.is_dir())
                )

        self._snapshot = current

    def _build_snapshot(self) -> dict[Path, tuple[float, int]]:
        snapshot: dict[Path, tuple[float, int]] = {}
        for root in self._watcher.paths:
            if not root.exists():
                continue
            if root.is_file():
                try:
                    stat = root.stat()
                except OSError:
                    continue
                snapshot[root] = (stat.st_mtime, stat.st_size)
                continue
            for path in self._iter_files(root):
                try:
                    stat = path.stat()
                except OSError:
                    continue
                snapshot[path] = (stat.st_mtime, stat.st_size)
        return snapshot

    @staticmethod
    def _iter_files(root: Path) -> list[Path]:
        paths: list[Path] = []
        try:
            entries = list(os.scandir(root))
        except OSError:
            return paths

        for entry in entries:
            path = Path(entry.path)
            if entry.is_dir(follow_symlinks=False):
                paths.extend(_PollingBackend._iter_files(path))
            else:
                paths.append(path)
        return paths


_Sentinel = object()


__all__ = [
    "EventType",
    "FileSystemEvent",
    "RealtimeWatcher",
]

