from __future__ import annotations

import os
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from auto_organizer.file_scanner import FileScanner
from auto_organizer.models import FileScanOptions


@pytest.fixture()
def temp_structure(tmp_path: Path) -> Path:
    (tmp_path / "visible.txt").write_text("hello", encoding="utf-8")
    (tmp_path / ".hidden.txt").write_text("secret", encoding="utf-8")
    nested = tmp_path / "nested"
    nested.mkdir()
    (nested / "data.log").write_text("log", encoding="utf-8")
    old_file = nested / "old.txt"
    old_file.write_text("old", encoding="utf-8")
    old_time = datetime.now() - timedelta(days=2)
    os.utime(old_file, (old_time.timestamp(), old_time.timestamp()))
    return tmp_path


def test_scan_respects_hidden_and_size_filters(temp_structure: Path) -> None:
    options = FileScanOptions(include_hidden=False, min_size=1, max_size=10)
    scanner = FileScanner(options=options)
    result = scanner.scan([temp_structure])
    scanned_paths = {candidate.path.name for candidate in result.candidates}
    assert "visible.txt" in scanned_paths
    assert "data.log" in scanned_paths
    assert ".hidden.txt" not in scanned_paths


def test_scan_filters_by_modified_date(temp_structure: Path) -> None:
    threshold = datetime.now() - timedelta(days=1)
    options = FileScanOptions(modified_after=threshold)
    scanner = FileScanner(options=options)
    result = scanner.scan([temp_structure])
    scanned_paths = {candidate.path.name for candidate in result.candidates}
    assert "old.txt" not in scanned_paths
