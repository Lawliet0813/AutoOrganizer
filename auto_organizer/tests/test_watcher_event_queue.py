"""Tests for watcher event queue merging and flushing."""
from __future__ import annotations

import time
from pathlib import Path

from auto_organizer.watcher.event_queue import EventQueue
from auto_organizer.watcher.types import EventType, FileSystemEvent


def make_event(path: Path, event_type: EventType) -> FileSystemEvent:
    return FileSystemEvent(path=path, event_type=event_type)


def test_event_queue_debounce_merges(tmp_path):
    emitted: list[list[FileSystemEvent]] = []
    queue = EventQueue(emitted.append, debounce_interval=0.5, flush_interval=10)

    path = tmp_path / "file.txt"
    event1 = make_event(path, EventType.CREATED)
    event2 = make_event(path, EventType.MODIFIED)

    queue.add(event1)
    queue.add(event2)
    queue.flush_due(force=True)

    assert len(emitted) == 1
    assert emitted[0][0].event_type is EventType.CREATED


def test_event_queue_prefers_delete(tmp_path):
    emitted: list[list[FileSystemEvent]] = []
    queue = EventQueue(emitted.append, debounce_interval=0.5, flush_interval=10)

    path = tmp_path / "file.txt"
    queue.add(make_event(path, EventType.CREATED))
    queue.add(make_event(path, EventType.DELETED))
    queue.flush_due(force=True)

    assert emitted[0][0].event_type is EventType.DELETED


def test_event_queue_flushes_after_interval(tmp_path):
    emitted: list[list[FileSystemEvent]] = []
    queue = EventQueue(emitted.append, debounce_interval=0.05, flush_interval=0.1)

    path = tmp_path / "file.txt"
    queue.add(make_event(path, EventType.CREATED))
    queue.flush_due()
    assert emitted == []

    time.sleep(0.12)
    queue.flush_due()
    assert len(emitted) == 1
    assert emitted[0][0].path == path
