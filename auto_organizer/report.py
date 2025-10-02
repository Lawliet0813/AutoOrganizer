"""Reporting helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from .config import FileInfo, Statistics


class ReportBuilder:
    """Generate simple textual reports for organization runs."""

    def build(self, stats: Statistics, categorized: Dict[str, List[FileInfo]]) -> str:
        lines = ["AutoOrganizer Report", "===================", ""]
        lines.append(f"Total files scanned: {stats.total_files}")
        lines.append(f"Processed files: {stats.processed_files}")
        lines.append(f"Skipped items: {stats.skipped_items}")
        lines.append(f"Duplicates: {stats.duplicates}")
        lines.append(f"Errors: {stats.errors}")
        lines.append("")
        for category, items in categorized.items():
            lines.append(f"{category}: {len(items)} files")
        return "\n".join(lines)

    def save(self, report: str, path: Path) -> None:
        path.write_text(report, encoding="utf-8")
