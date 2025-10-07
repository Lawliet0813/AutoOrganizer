"""Tests for :mod:`auto_organizer.realtime_watcher`."""
from __future__ import annotations

import time
from pathlib import Path

import pytest

from auto_organizer.realtime_watcher import EventType, FileSystemEvent, RealtimeWatcher


@pytest.fixture()
def watcher_factory():
    created_watchers: list[RealtimeWatcher] = []

    def factory(**kwargs: object) -> RealtimeWatcher:
        events: list[list[FileSystemEvent]] = []

        callback = kwargs.pop("callback", lambda batch: events.append(batch))
        watcher = RealtimeWatcher(
            paths=[Path("/tmp")],
            callback=callback,
            backend_factory=lambda _: None,
            **kwargs,
        )
        created_watchers.append(watcher)
        watcher._test_batches = events  # type: ignore[attr-defined]
        return watcher

    yield factory

    for watcher in created_watchers:
        watcher.stop()


def collect_batches(watcher: RealtimeWatcher) -> list[list[FileSystemEvent]]:
    return getattr(watcher, "_test_batches")  # type: ignore[no-any-return]


def wait_for_batches(watcher: RealtimeWatcher, *, timeout: float = 1.0) -> list[list[FileSystemEvent]]:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        batches = collect_batches(watcher)
        if batches:
            return batches
        time.sleep(0.01)
    return collect_batches(watcher)


def test_realtime_watcher_batches_events(watcher_factory):
    watcher = watcher_factory(batch_interval=0.05, debounce_interval=0.01)
    watcher.start()

    watcher.enqueue("/tmp/file1.txt", EventType.CREATED)
    watcher.enqueue("/tmp/file2.txt", EventType.MODIFIED)

    batches = wait_for_batches(watcher)

    assert len(batches) == 1
    emitted = batches[0]
    assert {event.path.name for event in emitted} == {"file1.txt", "file2.txt"}


def test_realtime_watcher_debounces_events(watcher_factory):
    watcher = watcher_factory(batch_interval=0.05, debounce_interval=0.1)
    watcher.start()

    watcher.enqueue("/tmp/file1.txt", EventType.CREATED)
    time.sleep(0.02)
    watcher.enqueue("/tmp/file1.txt", EventType.MODIFIED)

    batches = wait_for_batches(watcher)

    assert len(batches) == 1
    emitted = batches[0]
    assert len(emitted) == 1
    assert emitted[0].event_type is EventType.CREATED


def test_realtime_watcher_blacklist_patterns(watcher_factory):
    watcher = watcher_factory(
        batch_interval=0.05,
        debounce_interval=0.01,
        blacklist_patterns=["*.tmp"],
    )
    watcher.start()

    watcher.enqueue("/tmp/file1.txt", EventType.CREATED)
    watcher.enqueue("/tmp/file1.tmp", EventType.CREATED)

    batches = wait_for_batches(watcher)

    assert len(batches) == 1
    emitted = batches[0]
    assert len(emitted) == 1
    assert emitted[0].path.name == "file1.txt"


def test_realtime_watcher_flushes_on_stop(watcher_factory):
    watcher = watcher_factory(batch_interval=10, debounce_interval=0.01)
    watcher.start()

    watcher.enqueue("/tmp/file1.txt", EventType.CREATED)
    watcher.stop()

    batches = collect_batches(watcher)
    assert len(batches) == 1
    assert batches[0][0].path.name == "file1.txt"
