"""Main AutoOrganizer orchestration."""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from .classifier import ClassificationEngine
from .config import FileInfo, OrganizeOptions, OrganizeResult, OrganizeTask
from .filters import SystemFileFilter
from .mover import FileMover
from .report import ReportBuilder
from .scanner import FileScanner


class AutoOrganizer:
    """Coordinate scanning, filtering, classification, and moving."""

    def __init__(self, options: Optional[OrganizeOptions] = None) -> None:
        self.options = options or OrganizeOptions()
        self.filter = SystemFileFilter(self.options.whitelist_patterns)
        self.scanner = FileScanner(self.options, self.filter)
        self.classifier = ClassificationEngine()
        self.mover = FileMover(self.options.duplicate_strategy)
        self.reporter = ReportBuilder()

    def load_custom_rules(self, path: Path) -> None:
        self.classifier.load_custom_rules(path)

    def organize(self, source_folders: Iterable[Path], target_folder: Path) -> OrganizeResult:
        task = OrganizeTask(
            task_id=str(uuid.uuid4()),
            execution_time=datetime.now(),
            source_folders=[Path(folder) for folder in source_folders],
            target_folder=Path(target_folder),
            options=self.options,
        )

        categorized: Dict[str, List[FileInfo]] = defaultdict(list)
        errors: List[str] = []

        for folder in task.source_folders:
            for file_info in self.scanner.scan(folder):
                task.statistics.total_files += 1
                if file_info.is_system_file:
                    task.statistics.skipped_items += 1
                    continue

                category, confidence = self.classifier.classify(file_info)
                file_info.category = category
                file_info.confidence = confidence

                destination = target_folder / category

                try:
                    new_path = self.mover.transactional_move(file_info, destination)
                except Exception as exc:  # noqa: BLE001
                    error_message = f"Failed to move {file_info.file_path}: {exc}"
                    errors.append(error_message)
                    task.statistics.errors += 1
                    file_info.process_status = "error"
                    file_info.error_message = str(exc)
                    continue

                if new_path is None:
                    task.statistics.skipped_items += 1
                    file_info.process_status = "skipped"
                    continue

                if new_path != destination / file_info.file_name:
                    task.statistics.duplicates += 1
                task.statistics.processed_files += 1
                file_info.process_status = "moved"
                categorized[category].append(file_info)

        if self.options.generate_report:
            report = self.reporter.build(task.statistics, categorized)
            report_path = target_folder / "AutoOrganizer_report.txt"
            self.reporter.save(report, report_path)

        return OrganizeResult(
            success=task.statistics.errors == 0,
            processed_files=task.statistics.processed_files,
            skipped_files=task.statistics.skipped_items,
            duplicates=task.statistics.duplicates,
            errors=errors,
            details={
                category: [f.file_path for f in items]
                for category, items in categorized.items()
            },
        )
