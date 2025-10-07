"""File scanning module responsible for producing candidate files."""
from __future__ import annotations

import fnmatch
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Iterator, Sequence

from .logger import configure_logging, log_event
from .models import FileCandidate, FileScanOptions, ScanResult

LOGGER_NAME = "auto_organizer.scanner"


class FileScanner:
    """Walks directories and yields :class:`FileCandidate` objects."""

    def __init__(
        self,
        options: FileScanOptions | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self.options = options or FileScanOptions()
        self.logger = logger or logging.getLogger(LOGGER_NAME)
        if not self.logger.handlers:
            configure_logging()

    def scan(self, roots: Sequence[str | Path]) -> ScanResult:
        """Scan the given *roots* and return a :class:`ScanResult`."""

        normalized_roots = [Path(root).expanduser() for root in roots]
        candidates: list[FileCandidate] = []
        total_size = 0

        for root in normalized_roots:
            if not root.exists():
                log_event(
                    self.logger,
                    level=logging.WARNING,
                    action="scan.skip",
                    message=f"Root does not exist: {root}",
                    extra={"path": str(root)},
                )
                continue

            for candidate in self._scan_path(root, current_depth=0):
                candidates.append(candidate)
                total_size += candidate.size

        return ScanResult(
            candidates=candidates,
            total_files=len(candidates),
            total_bytes=total_size,
        )

    def _scan_path(self, path: Path, *, current_depth: int) -> Iterator[FileCandidate]:
        if path.is_file() or (path.is_symlink() and not self.options.follow_symlinks):
            candidate = self._build_candidate(path)
            if candidate:
                yield candidate
            return

        if path.is_dir():
            if not self._should_descend(current_depth):
                return

            try:
                with os.scandir(path) as entries:
                    for entry in entries:
                        entry_path = Path(entry.path)
                        next_depth = current_depth + 1
                        if entry.is_dir(follow_symlinks=self.options.follow_symlinks):
                            if self._should_skip_directory(entry_path):
                                continue
                            yield from self._scan_path(entry_path, current_depth=next_depth)
                        elif entry.is_file(follow_symlinks=self.options.follow_symlinks):
                            candidate = self._build_candidate(entry_path, entry=entry)
                            if candidate:
                                yield candidate
                        elif entry.is_symlink():
                            if not self.options.follow_symlinks:
                                continue
                            if entry_path.exists():
                                yield from self._scan_path(entry_path, current_depth=next_depth)
            except PermissionError:
                log_event(
                    self.logger,
                    level=logging.WARNING,
                    action="scan.permission_denied",
                    message=f"Permission denied: {path}",
                    extra={"path": str(path)},
                )

    def _should_descend(self, depth: int) -> bool:
        if self.options.max_depth is None:
            return True
        return depth <= self.options.max_depth

    def _should_skip_directory(self, path: Path) -> bool:
        name = path.name
        if not self.options.include_hidden and name.startswith('.'):
            return True
        for pattern in self.options.exclude_patterns:
            if fnmatch.fnmatch(name, pattern) or fnmatch.fnmatch(str(path), pattern):
                return True
        return False

    def _build_candidate(
        self,
        path: Path,
        *,
        entry: os.DirEntry[str] | None = None,
    ) -> FileCandidate | None:
        if not self._should_include(path):
            return None

        try:
            stat_result = entry.stat(follow_symlinks=self.options.follow_symlinks) if entry else path.stat()
        except FileNotFoundError:
            log_event(
                self.logger,
                level=logging.INFO,
                action="scan.missing",
                message=f"File disappeared during scan: {path}",
                extra={"path": str(path)},
            )
            return None

        candidate = FileCandidate(
            path=path,
            size=stat_result.st_size,
            modified_at=datetime.fromtimestamp(stat_result.st_mtime),
            is_symlink=path.is_symlink(),
        )
        return candidate

    def _should_include(self, path: Path) -> bool:
        name = path.name
        if not self.options.include_hidden and name.startswith('.'):
            return False

        if self.options.include_patterns:
            if not any(fnmatch.fnmatch(name, pattern) or fnmatch.fnmatch(str(path), pattern) for pattern in self.options.include_patterns):
                return False

        if self.options.exclude_patterns:
            if any(fnmatch.fnmatch(name, pattern) or fnmatch.fnmatch(str(path), pattern) for pattern in self.options.exclude_patterns):
                return False

        try:
            stat_result = path.stat()
        except FileNotFoundError:
            return False

        size = stat_result.st_size
        if self.options.min_size is not None and size < self.options.min_size:
            return False
        if self.options.max_size is not None and size > self.options.max_size:
            return False

        modified_at = datetime.fromtimestamp(stat_result.st_mtime)
        if self.options.modified_before and modified_at >= self.options.modified_before:
            return False
        if self.options.modified_after and modified_at <= self.options.modified_after:
            return False

        return True
