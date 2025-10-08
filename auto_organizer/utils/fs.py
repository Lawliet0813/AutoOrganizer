"""Filesystem helpers used by AutoOrganizer."""
from __future__ import annotations

from pathlib import Path


def ensure_directory(path: Path) -> Path:
    """Ensure that *path* exists as a directory and return it."""

    path.mkdir(parents=True, exist_ok=True)
    return path


def unique_path(base: Path, *, reserved: set[Path] | None = None) -> Path:
    """Return a unique path derived from *base*.

    The function checks both the filesystem and the ``reserved`` set to avoid
    collisions. The provided ``reserved`` set will be updated with the selected
    path when supplied.
    """

    reserved_paths: set[Path] = reserved if reserved is not None else set()
    candidate = base
    counter = 1
    while candidate in reserved_paths or candidate.exists():
        candidate = candidate.with_name(f"{base.stem}_{counter}{base.suffix}")
        counter += 1
    reserved_paths.add(candidate)
    return candidate


__all__ = ["ensure_directory", "unique_path"]
