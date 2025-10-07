"""Core dataclasses shared across AutoOrganizer modules."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Iterable, Sequence


@dataclass(slots=True)
class FileCandidate:
    """Represents a file discovered by :mod:`file_scanner`."""

    path: Path
    size: int
    modified_at: datetime
    is_symlink: bool = False
    tags: set[str] = field(default_factory=set)


@dataclass(slots=True)
class FileScanOptions:
    """Configuration options for the :class:`~auto_organizer.file_scanner.FileScanner`."""

    recursive: bool = True
    follow_symlinks: bool = False
    max_depth: int | None = None
    include_hidden: bool = False
    include_patterns: Sequence[str] = field(default_factory=list)
    exclude_patterns: Sequence[str] = field(default_factory=list)
    min_size: int | None = None
    max_size: int | None = None
    modified_before: datetime | None = None
    modified_after: datetime | None = None


@dataclass(slots=True)
class ScanResult:
    """Container for scan results and summary statistics."""

    candidates: Iterable[FileCandidate]
    total_files: int
    total_bytes: int


@dataclass(slots=True)
class ClassificationResult:
    """Represents the output of the classification engine."""

    category: str
    confidence: float
    rationale: str


@dataclass(slots=True)
class PlanItem:
    """Description of an action the mover should execute."""

    source: Path
    destination: Path
    operation: str
    same_volume: bool
    size: int
    conflict: bool
    estimated_ms: float | None = None
    hash_digest: str | None = None
