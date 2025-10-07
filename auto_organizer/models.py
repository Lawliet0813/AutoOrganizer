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
class FilterDecision:
    """Decision returned by :mod:`system_filter` for a candidate."""

    candidate: FileCandidate
    should_skip: bool
    reason: str | None = None
    flags: set[str] = field(default_factory=set)

    def to_dict(self) -> dict[str, object]:
        """Serialize the decision for JSON output."""

        return {
            "path": str(self.candidate.path),
            "should_skip": self.should_skip,
            "reason": self.reason,
            "flags": sorted(self.flags),
            "size": self.candidate.size,
        }


@dataclass(slots=True)
class PlanSummary:
    """Aggregated statistics for a generated plan."""

    total_candidates: int
    planned: int
    skipped: int
    total_bytes: int
    categories: dict[str, int] = field(default_factory=dict)


@dataclass(slots=True)
class Plan:
    """Full representation of a dry-run plan."""

    sources: Sequence[str]
    destination_root: Path
    items: list[PlanItem]
    skipped: list[FilterDecision]
    summary: PlanSummary
    generated_at: datetime


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
    category: str | None = None
    confidence: float | None = None
    rationale: str | None = None
    flags: set[str] = field(default_factory=set)


@dataclass(slots=True)
class RollbackStep:
    """Action that can undo a move performed by the mover."""

    source: Path
    destination: Path
    operation: str


@dataclass(slots=True)
class ExecutionSummary:
    """Aggregated statistics produced by the mover."""

    processed: int
    succeeded: int
    skipped: int
    failed: int
    bytes_processed: int
    errors: list[str] = field(default_factory=list)
