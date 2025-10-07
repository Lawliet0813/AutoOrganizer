"""Unified report generation for AutoOrganizer runs."""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, Mapping


@dataclass(slots=True)
class RunSummary:
    """Normalized data consumed by :class:`ReportGenerator`."""

    started_at: datetime
    finished_at: datetime
    classification_counts: Mapping[str, int]
    moved_files: int
    skipped_files: int
    reclaimed_bytes: int
    errors: Iterable[Mapping[str, str]]

    @property
    def duration_seconds(self) -> float:
        return max((self.finished_at - self.started_at).total_seconds(), 0.0)


class ReportGenerator:
    """Produce consolidated JSON and text reports."""

    def build_payload(self, summary: RunSummary) -> dict[str, object]:
        total_processed = summary.moved_files + summary.skipped_files
        errors = list(summary.errors)
        return {
            "started_at": summary.started_at.isoformat(),
            "finished_at": summary.finished_at.isoformat(),
            "duration_seconds": summary.duration_seconds,
            "classification": dict(sorted(summary.classification_counts.items())),
            "totals": {
                "processed": total_processed,
                "moved": summary.moved_files,
                "skipped": summary.skipped_files,
                "errors": len(errors),
                "reclaimed_bytes": summary.reclaimed_bytes,
            },
            "errors": errors,
        }

    def write(self, payload: Mapping[str, object], destination: str | Path) -> tuple[Path, Path]:
        """Write *payload* as JSON and text into *destination*."""

        destination_path = Path(destination)
        destination_path.mkdir(parents=True, exist_ok=True)

        json_path = destination_path / "report.json"
        txt_path = destination_path / "report.txt"

        json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

        lines: list[str] = [
            "AutoOrganizer Run Report",
            "========================",
            f"Start: {payload['started_at']}",
            f"End: {payload['finished_at']}",
            f"Duration: {payload['duration_seconds']:.2f}s",
            "",
            "Classification summary:",
        ]
        classification = payload.get("classification", {})
        for key, value in classification.items():
            lines.append(f"  - {key}: {value}")

        totals = payload.get("totals", {})
        lines.extend(
            [
                "",
                "Totals:",
                f"  processed: {totals.get('processed', 0)}",
                f"  moved: {totals.get('moved', 0)}",
                f"  skipped: {totals.get('skipped', 0)}",
                f"  errors: {totals.get('errors', 0)}",
                f"  reclaimed_bytes: {totals.get('reclaimed_bytes', 0)}",
            ]
        )

        errors = payload.get("errors", [])
        if errors:
            lines.extend(["", "Errors:"])
            for error in errors:
                message = error.get("message", "unknown error")
                path = error.get("path", "?")
                lines.append(f"  - {path}: {message}")

        txt_path.write_text("\n".join(lines), encoding="utf-8")
        return json_path, txt_path


__all__ = ["ReportGenerator", "RunSummary"]
