from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from auto_organizer.classifier import ClassificationEngine
from auto_organizer.models import FileCandidate
from auto_organizer.planner import Planner


def make_candidate(tmp_path: Path, name: str, size: int = 1024) -> FileCandidate:
    file_path = tmp_path / name
    file_path.write_bytes(b"x" * size)
    return FileCandidate(
        path=file_path,
        size=size,
        modified_at=datetime.now(timezone.utc),
        is_symlink=False,
    )


def test_planner_creates_plan_with_conflicts(tmp_path) -> None:
    rules = {"extension": {".txt": "docs"}}
    planner = Planner(tmp_path / "dest", category_mapping={"docs": "Documents"}, classifier=ClassificationEngine(rules))

    candidate1 = make_candidate(tmp_path, "report.txt")
    candidate2 = make_candidate(tmp_path, "report.txt")

    result = planner.plan([candidate1, candidate2])
    assert len(result.items) == 2
    assert result.conflicts  # second item should conflict
    assert result.items[0].destination.parent.name == "Documents"
    assert result.items[0].operation in {"rename", "copy"}
