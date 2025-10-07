"""Rollback utilities to restore files from `rollback.json`."""
from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

from .logger import log_event


@dataclass(slots=True)
class RollbackEntry:
    original_path: Path
    backup_path: Path
    sha256: str
    size: int | None = None


class RollbackManager:
    def __init__(self, logger) -> None:
        self.logger = logger

    def load_entries(self, rollback_file: str | Path) -> list[RollbackEntry]:
        payload = json.loads(Path(rollback_file).read_text(encoding="utf-8"))
        entries = []
        for raw in payload.get("entries", []):
            entry = RollbackEntry(
                original_path=Path(raw["original_path"]).expanduser(),
                backup_path=Path(raw["backup_path"]).expanduser(),
                sha256=raw["sha256"],
                size=raw.get("size"),
            )
            entries.append(entry)
        return entries

    def restore(
        self,
        entries: Iterable[RollbackEntry],
        *,
        dry_run: bool = False,
        target_filter: Sequence[str] | None = None,
    ) -> list[Path]:
        restored: list[Path] = []
        for entry in entries:
            if target_filter and not _matches(entry, target_filter):
                continue

            if not entry.backup_path.exists():
                log_event(
                    self.logger,
                    level=20,
                    action="rollback.missing_backup",
                    message=f"Missing backup file: {entry.backup_path}",
                    extra={"path": str(entry.backup_path)},
                )
                continue

            if not _verify_hash(entry.backup_path, entry.sha256):
                log_event(
                    self.logger,
                    level=40,
                    action="rollback.hash_mismatch",
                    message=f"Checksum mismatch for {entry.backup_path}",
                    extra={"path": str(entry.backup_path)},
                )
                continue

            destination = entry.original_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            if not dry_run:
                shutil.move(str(entry.backup_path), str(destination))
            restored.append(destination)
            log_event(
                self.logger,
                level=20,
                action="rollback.restore",
                message=f"Restored {destination}",
                extra={"path": str(destination)},
            )
        return restored


def _verify_hash(path: Path, expected: str) -> bool:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest() == expected


def _matches(entry: RollbackEntry, target_filter: Sequence[str]) -> bool:
    str_path = str(entry.original_path)
    backup_str = str(entry.backup_path)
    return any(token in str_path or token in backup_str for token in target_filter)


__all__ = ["RollbackManager", "RollbackEntry"]
