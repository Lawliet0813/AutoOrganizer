"""Filesystem scanning utilities."""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Iterator, List

from .config import FileInfo, OrganizeOptions
from .filters import SystemFileFilter


class FileScanner:
    """Scan directories and collect metadata according to options."""

    def __init__(self, options: OrganizeOptions, system_filter: SystemFileFilter) -> None:
        self.options = options
        self.system_filter = system_filter

    def scan(self, folder: Path) -> List[FileInfo]:
        """Scan a folder and return metadata for eligible files."""

        files: List[FileInfo] = []
        for info in self._iter_files(folder):
            if self.system_filter.should_skip(info.file_name, info.file_size):
                info.is_system_file = True
                info.process_status = "skipped"
                files.append(info)
                continue

            if self.system_filter.is_whitelisted(info.file_name):
                info.is_system_file = False
            files.append(info)
        return files

    def _iter_files(self, folder: Path) -> Iterator[FileInfo]:
        stack: List[Path] = [folder]
        while stack:
            current = stack.pop()
            if not current.exists():
                continue
            with os.scandir(current) as it:
                for entry in it:
                    if entry.is_symlink():
                        continue
                    if entry.is_dir():
                        if self.options.recursive:
                            stack.append(Path(entry.path))
                        continue

                    stats = entry.stat()
                    yield FileInfo(
                        file_path=Path(entry.path),
                        file_name=entry.name,
                        file_extension=Path(entry.name).suffix.lower(),
                        file_size=stats.st_size,
                        creation_date=_safe_datetime(stats.st_ctime),
                        modification_date=_safe_datetime(stats.st_mtime),
                        source_folder=current,
                    )


def _safe_datetime(timestamp: float) -> datetime:
    try:
        return datetime.fromtimestamp(timestamp)
    except (OverflowError, OSError, ValueError):
        return datetime.fromtimestamp(0)
