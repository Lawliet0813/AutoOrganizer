"""SQLite backed deduplication index and helper utilities."""
from __future__ import annotations

import hashlib
import logging
import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Iterator, Sequence


LOGGER = logging.getLogger("auto_organizer.dedup")


@dataclass(slots=True)
class DedupRecord:
    """Represents a single file record stored in the dedup index."""

    hash: str
    path: Path
    size: int
    modified_at: datetime

    def to_dict(self) -> dict[str, str | int]:
        return {
            "hash": self.hash,
            "path": str(self.path),
            "size": self.size,
            "modified_at": self.modified_at.isoformat(),
        }


class DedupIndex:
    """A lightweight SQLite service that tracks file hashes and duplicates."""

    def __init__(self, db_path: str | os.PathLike[str] | None = None) -> None:
        default_path = Path.home() / ".autoorganizer" / "dedup_index.db"
        self.db_path = Path(db_path or default_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row
        self._initialize_schema()

    # -- public API -----------------------------------------------------
    def index_paths(self, paths: Sequence[str | os.PathLike[str]]) -> list[DedupRecord]:
        """Index all files under *paths* and return the indexed records."""

        records: list[DedupRecord] = []
        for file_path in self._iter_files(paths):
            try:
                stat_result = file_path.stat()
            except FileNotFoundError:
                continue

            digest = self._hash_file(file_path)
            record = DedupRecord(
                hash=digest,
                path=file_path,
                size=stat_result.st_size,
                modified_at=datetime.fromtimestamp(stat_result.st_mtime),
            )
            records.append(record)
            self._conn.execute(
                """
                INSERT INTO dedup_index(hash, path, size, modified_at)
                VALUES(:hash, :path, :size, :modified_at)
                ON CONFLICT(path) DO UPDATE
                SET hash=excluded.hash,
                    size=excluded.size,
                    modified_at=excluded.modified_at
                """,
                {
                    "hash": record.hash,
                    "path": str(record.path),
                    "size": record.size,
                    "modified_at": record.modified_at.isoformat(),
                },
            )

        self._conn.commit()
        return records

    def get_duplicates(self) -> list[list[DedupRecord]]:
        """Return duplicate groups stored in the database."""

        cursor = self._conn.execute(
            """
            SELECT hash, path, size, modified_at
            FROM dedup_index
            WHERE hash IN (
                SELECT hash FROM dedup_index
                GROUP BY hash HAVING COUNT(*) > 1
            )
            ORDER BY hash, modified_at, path
            """
        )
        groups: list[list[DedupRecord]] = []
        current_hash: str | None = None
        current_group: list[DedupRecord] = []
        for row in cursor:
            record = DedupRecord(
                hash=row["hash"],
                path=Path(row["path"]),
                size=row["size"],
                modified_at=datetime.fromisoformat(row["modified_at"]),
            )
            if current_hash != record.hash:
                if current_group:
                    groups.append(current_group)
                current_group = [record]
                current_hash = record.hash
            else:
                current_group.append(record)
        if current_group:
            groups.append(current_group)
        return groups

    def clean_duplicates(self, *, dry_run: bool = False) -> list[tuple[DedupRecord, Path]]:
        """Remove duplicate files while keeping the oldest file for each hash."""

        deletions: list[tuple[DedupRecord, Path]] = []
        for group in self.get_duplicates():
            keeper = min(group, key=lambda record: record.modified_at)
            for record in group:
                if record.path == keeper.path:
                    continue
                deletions.append((record, keeper.path))
                if dry_run:
                    continue
                try:
                    record.path.unlink()
                except FileNotFoundError:
                    pass
                self._conn.execute(
                    "DELETE FROM dedup_index WHERE path = ?",
                    (str(record.path),),
                )
        if not dry_run:
            self._conn.commit()
        return deletions

    def write_reports(
        self,
        duplicates: Sequence[Sequence[DedupRecord]],
        output_dir: str | os.PathLike[str],
    ) -> tuple[Path, Path]:
        """Write JSON and text reports summarising *duplicates*."""

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        json_path = output_path / "dedup_report.json"
        txt_path = output_path / "dedup_report.txt"

        total_wasted = sum(
            record.size
            for group in duplicates
            for record in group[1:]
        )
        payload = {
            "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "groups": [
                {
                    "hash": group[0].hash,
                    "count": len(group),
                    "size_each": group[0].size,
                    "wasted_bytes": sum(item.size for item in group[1:]),
                    "files": [rec.to_dict() for rec in group],
                }
                for group in duplicates
            ],
            "total_groups": len(duplicates),
            "total_wasted_bytes": total_wasted,
        }

        import json

        json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

        lines = [
            "AutoOrganizer Deduplication Report",
            "================================",
            f"Groups: {payload['total_groups']}",
            f"Potential space recovery: {payload['total_wasted_bytes']} bytes",
            "",
        ]
        for group in duplicates:
            lines.append(f"Hash: {group[0].hash} ({len(group)} files)")
            for record in group:
                lines.append(f"  - {record.path} [{record.size} bytes]")
            lines.append("")
        txt_path.write_text("\n".join(lines), encoding="utf-8")
        return json_path, txt_path

    def purge_missing(self) -> int:
        """Remove database entries whose files no longer exist."""

        cursor = self._conn.execute("SELECT path FROM dedup_index")
        removed = 0
        for (path_str,) in cursor.fetchall():
            path = Path(path_str)
            if not path.exists():
                self._conn.execute("DELETE FROM dedup_index WHERE path = ?", (path_str,))
                removed += 1
        if removed:
            self._conn.commit()
        return removed

    def close(self) -> None:
        self._conn.close()

    # -- helpers --------------------------------------------------------
    def _initialize_schema(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS dedup_index (
                hash TEXT NOT NULL,
                path TEXT PRIMARY KEY,
                size INTEGER NOT NULL,
                modified_at TEXT NOT NULL
            )
            """
        )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_dedup_hash ON dedup_index(hash)"
        )
        self._conn.commit()

    def _hash_file(self, path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as fh:
            for chunk in iter(lambda: fh.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _iter_files(self, paths: Iterable[str | os.PathLike[str]]) -> Iterator[Path]:
        for item in paths:
            path = Path(item).expanduser()
            if path.is_file():
                yield path
            elif path.is_dir():
                for root, _, files in os.walk(path):
                    for filename in files:
                        yield Path(root, filename)


__all__ = ["DedupIndex", "DedupRecord"]
