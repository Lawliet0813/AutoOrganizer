from __future__ import annotations

import json
import logging
from pathlib import Path

from auto_organizer.file_mover import FileMover
from auto_organizer.models import PlanItem


def make_logger(name: str = "auto_organizer.test") -> logging.Logger:
    logger = logging.getLogger(name)
    logger.handlers = []
    logger.addHandler(logging.NullHandler())
    logger.setLevel(logging.INFO)
    return logger


def test_rename_creates_rollback(tmp_path: Path) -> None:
    source_dir = tmp_path / "src"
    destination_dir = tmp_path / "dst"
    source_dir.mkdir()
    destination_dir.mkdir()
    source_file = source_dir / "sample.txt"
    source_file.write_text("content", encoding="utf-8")
    plan_item = PlanItem(
        source=source_file,
        destination=destination_dir / "sample.txt",
        operation="rename",
        same_volume=True,
        size=source_file.stat().st_size,
        conflict=False,
    )
    mover = FileMover(logger=make_logger("auto_organizer.rename_test"))
    rollback_path = tmp_path / "rollback.json"
    summary = mover.execute_plan([plan_item], rollback_path)
    assert summary.succeeded == 1
    assert (destination_dir / "sample.txt").exists()
    assert not source_file.exists()
    data = json.loads(rollback_path.read_text(encoding="utf-8"))
    assert data[0]["operation"] == "rename"
    script = rollback_path.with_suffix(".sh").read_text(encoding="utf-8")
    assert "mv" in script


def test_copy_with_verification(tmp_path: Path) -> None:
    source_dir = tmp_path / "src"
    destination_dir = tmp_path / "dst"
    source_dir.mkdir()
    destination_dir.mkdir()
    source_file = source_dir / "sample.bin"
    source_file.write_bytes(b"binary-data" * 10)
    plan_item = PlanItem(
        source=source_file,
        destination=destination_dir / "sample.bin",
        operation="copy",
        same_volume=False,
        size=source_file.stat().st_size,
        conflict=False,
    )
    mover = FileMover(logger=make_logger("auto_organizer.copy_test"))
    rollback_path = tmp_path / "rollback_copy.json"
    summary = mover.execute_plan([plan_item], rollback_path)
    assert summary.succeeded == 1
    assert (destination_dir / "sample.bin").exists()
    assert not source_file.exists()
    assert plan_item.hash_digest is not None
    rollback = json.loads(rollback_path.read_text(encoding="utf-8"))
    assert rollback[0]["operation"] == "restore"
