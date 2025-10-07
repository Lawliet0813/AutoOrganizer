from __future__ import annotations

import json
from pathlib import Path

from auto_organizer.logger import configure_logging, next_log_path
from auto_organizer.rollback import RollbackManager


def _write_rollback(tmp_path: Path, entries: list[dict]) -> Path:
    payload = {"entries": entries}
    rollback_path = tmp_path / "rollback.json"
    rollback_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return rollback_path


def test_rollback_restores_file(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    logger = configure_logging(next_log_path("rollback-test"))
    manager = RollbackManager(logger)

    original = tmp_path / "original.txt"
    backup = tmp_path / "backup.txt"
    backup.write_text("payload", encoding="utf-8")
    digest = "239f59ed55e737c77147cf55ad0c1b030b6d7ee748a7426952f9b852d5a935e5"

    rollback_file = _write_rollback(
        tmp_path,
        [
            {
                "original_path": str(original),
                "backup_path": str(backup),
                "sha256": digest,
            }
        ],
    )

    entries = manager.load_entries(rollback_file)
    restored = manager.restore(entries)
    assert original.exists()
    assert restored == [original]


def test_rollback_skips_hash_mismatch(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    logger = configure_logging(next_log_path("rollback-test"))
    manager = RollbackManager(logger)

    original = tmp_path / "original.txt"
    backup = tmp_path / "backup.txt"
    backup.write_text("payload", encoding="utf-8")

    rollback_file = _write_rollback(
        tmp_path,
        [
            {
                "original_path": str(original),
                "backup_path": str(backup),
                "sha256": "deadbeef",
            }
        ],
    )

    entries = manager.load_entries(rollback_file)
    restored = manager.restore(entries)
    assert restored == []
    assert backup.exists()
