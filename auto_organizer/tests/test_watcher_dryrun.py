"""Tests for the watcher dry-run pipeline."""
from __future__ import annotations

from pathlib import Path

from auto_organizer.classifier import ClassificationEngine
from auto_organizer.watcher.dryrun import generate_move_plan, render_move_plan_json
from auto_organizer.watcher.types import EventType, FileSystemEvent


def test_generate_move_plan(tmp_path):
    watched_file = tmp_path / "sample.txt"
    watched_file.write_text("hello")

    events = [FileSystemEvent(path=watched_file, event_type=EventType.CREATED)]

    classifier = ClassificationEngine(rules={"extension": {".txt": "docs"}})
    destination_root = tmp_path / "organized"

    entries = generate_move_plan(
        events,
        destination_root=destination_root,
        classifier=classifier,
        category_mapping={"docs": "Documents"},
    )

    assert len(entries) == 1
    entry = entries[0]
    assert entry.path == str(watched_file)
    assert entry.predicted_category == "docs"
    assert entry.confidence == 1.0
    expected_target = destination_root / "Documents" / watched_file.name
    assert entry.target == str(expected_target)
    assert entry.conflict is False


def test_render_move_plan_json(tmp_path):
    watched_file = tmp_path / "sample.txt"
    events = [FileSystemEvent(path=watched_file, event_type=EventType.DELETED)]

    # Deleted file should be ignored resulting in empty plan.
    entries = generate_move_plan(events, destination_root=tmp_path)
    assert entries == []

    json_output = render_move_plan_json(entries)
    assert json_output == "[]"
