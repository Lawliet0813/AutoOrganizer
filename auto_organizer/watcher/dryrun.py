"""Dry-run utilities for the watcher subsystem."""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, Mapping, Sequence

from ..classifier import ClassificationEngine
from ..models import FileCandidate
from ..planner import Planner
from .types import EventType, FileSystemEvent


@dataclass(slots=True)
class MovePlanEntry:
    """Serializable entry for the watcher dry-run output."""

    path: str
    predicted_category: str
    target: str
    confidence: float
    conflict: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "path": self.path,
            "predicted_category": self.predicted_category,
            "target": self.target,
            "confidence": self.confidence,
            "conflict": self.conflict,
        }


def generate_move_plan(
    events: Sequence[FileSystemEvent],
    *,
    destination_root: str | Path,
    classifier: ClassificationEngine | None = None,
    category_mapping: Mapping[str, str] | None = None,
) -> list[MovePlanEntry]:
    """Produce a dry-run move plan for *events*.

    Only creation, modification and move events are considered. Missing files are
    ignored. The function returns a list of :class:`MovePlanEntry` objects.
    """

    classifier = classifier or ClassificationEngine()
    planner = Planner(
        destination_root=destination_root,
        category_mapping=category_mapping,
        classifier=classifier,
    )

    candidates: list[FileCandidate] = []
    classifications: list[tuple[str, float]] = []

    for event in events:
        if event.event_type not in {EventType.CREATED, EventType.MODIFIED, EventType.MOVED}:
            continue
        path = event.dest_path or event.path
        if not path.exists() or path.is_dir():
            continue
        stat = path.stat()
        candidate = FileCandidate(
            path=path,
            size=stat.st_size,
            modified_at=datetime.fromtimestamp(stat.st_mtime),
            is_symlink=path.is_symlink(),
        )
        result = classifier.classify(candidate)
        candidates.append(candidate)
        classifications.append((result.category, result.confidence))

    if not candidates:
        return []

    plan_result = planner.plan(candidates)
    entries: list[MovePlanEntry] = []

    for (category, confidence), plan_item in zip(classifications, plan_result.items):
        entries.append(
            MovePlanEntry(
                path=str(plan_item.source),
                predicted_category=category,
                target=str(plan_item.destination),
                confidence=confidence,
                conflict=plan_item.conflict,
            )
        )

    return entries


def render_move_plan_json(entries: Iterable[MovePlanEntry], *, indent: int = 2) -> str:
    """Serialize :class:`MovePlanEntry` objects into JSON."""

    return json.dumps([entry.to_dict() for entry in entries], indent=indent)


__all__ = ["MovePlanEntry", "generate_move_plan", "render_move_plan_json"]
