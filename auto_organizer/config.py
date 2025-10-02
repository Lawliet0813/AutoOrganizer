"""Configuration and data structures for AutoOrganizer."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, Iterable, List, Optional


class DuplicateStrategy(str, Enum):
    """Supported strategies for handling duplicate files."""

    RENAME = "rename"
    SKIP = "skip"
    OVERWRITE = "overwrite"


@dataclass
class OrganizeOptions:
    """Options that control how the organizer behaves."""

    recursive: bool = True
    handle_duplicates: bool = True
    duplicate_strategy: DuplicateStrategy = DuplicateStrategy.RENAME
    generate_report: bool = True
    silent_mode: bool = False
    whitelist_patterns: Iterable[str] = field(
        default_factory=lambda: ("重要資料", "專案檔案", "工作文件")
    )


@dataclass
class Statistics:
    """Statistics collected during an organization run."""

    total_files: int = 0
    processed_files: int = 0
    total_folders: int = 0
    processed_folders: int = 0
    skipped_items: int = 0
    errors: int = 0
    duplicates: int = 0


@dataclass
class FileInfo:
    """Detailed metadata about a file encountered during scanning."""

    file_path: Path
    file_name: str
    file_extension: str
    file_size: int
    creation_date: Optional[datetime]
    modification_date: Optional[datetime]
    source_folder: Path
    is_system_file: bool = False
    category: Optional[str] = None
    confidence: float = 0.0
    process_status: str = "pending"
    error_message: Optional[str] = None


@dataclass
class OrganizeTask:
    """Task definition describing a run of the organizer."""

    task_id: str
    execution_time: datetime
    source_folders: List[Path]
    target_folder: Path
    mode: str = "ultimate"
    naming_rule: str = "original"
    options: OrganizeOptions = field(default_factory=OrganizeOptions)
    statistics: Statistics = field(default_factory=Statistics)


@dataclass
class OrganizeResult:
    """Summary produced once the organizer finishes running."""

    success: bool
    processed_files: int
    skipped_files: int
    duplicates: int
    errors: List[str] = field(default_factory=list)
    details: Dict[str, List[Path]] = field(default_factory=dict)
