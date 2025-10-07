from __future__ import annotations

import json
from pathlib import Path

from auto_organizer.dedup_index import DedupIndex


def _create_duplicate_files(tmp_path: Path) -> None:
    payloads = {
        "a.txt": "duplicate",
        "b.txt": "duplicate",
        "c.txt": "duplicate",
        "unique.txt": "unique",
    }
    for name, text in payloads.items():
        (tmp_path / name).write_text(text, encoding="utf-8")


def test_dedup_index_reports_and_clean(tmp_path) -> None:
    db_path = tmp_path / "dedup.db"
    _create_duplicate_files(tmp_path)
    index = DedupIndex(db_path)
    try:
        index.index_paths([tmp_path])
        duplicates = index.get_duplicates()
        assert len(duplicates) == 1
        group = duplicates[0]
        assert len(group) == 3

        json_path, txt_path = index.write_reports(duplicates, tmp_path / "reports")
        assert json_path.exists()
        assert txt_path.exists()

        data = json.loads(json_path.read_text(encoding="utf-8"))
        assert data["total_groups"] == 1
        assert data["groups"][0]["count"] == 3

        deletions = index.clean_duplicates(dry_run=True)
        assert len(deletions) == 2
        assert all(item[0].path.exists() for item in deletions)

        index.clean_duplicates(dry_run=False)
        remaining = [
            path
            for path in tmp_path.iterdir()
            if path.suffix == ".txt" and path.name != "unique.txt"
        ]
        assert len(remaining) == 1
    finally:
        index.close()
