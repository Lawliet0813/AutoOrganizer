"""Planning utilities for AutoOrganizer dry-run and execution stages."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping

from .classifier import ClassificationEngine
from .models import FileCandidate, PlanItem


@dataclass(slots=True)
class PlanResult:
    """Container returned by :class:`Planner.plan`."""

    items: list[PlanItem]
    conflicts: list[PlanItem]
    total_bytes: int


class Planner:
    """Create :class:`PlanItem` objects from scanned candidates."""

    def __init__(
        self,
        destination_root: str | Path,
        *,
        category_mapping: Mapping[str, str] | None = None,
        classifier: ClassificationEngine | None = None,
    ) -> None:
        self.destination_root = Path(destination_root)
        self.category_mapping = dict(category_mapping or {})
        self.classifier = classifier or ClassificationEngine()

    def plan(self, candidates: Iterable[FileCandidate]) -> PlanResult:
        destination_cache: set[Path] = set()
        plan_items: list[PlanItem] = []
        conflicts: list[PlanItem] = []
        total_bytes = 0

        for candidate in candidates:
            classification = self.classifier.classify(candidate)
            category = classification.category
            total_bytes += candidate.size

            destination_dir = self._resolve_destination(category)
            destination = destination_dir / candidate.path.name
            same_volume = destination.anchor == candidate.path.anchor
            estimated_ms = self._estimate_duration(candidate.size, same_volume)

            plan_item = PlanItem(
                source=candidate.path,
                destination=destination,
                operation="rename" if same_volume else "copy",
                same_volume=same_volume,
                size=candidate.size,
                conflict=False,
                estimated_ms=estimated_ms,
            )

            if destination in destination_cache:
                plan_item.conflict = True
                conflicts.append(plan_item)
            else:
                destination_cache.add(destination)

            plan_items.append(plan_item)

        return PlanResult(items=plan_items, conflicts=conflicts, total_bytes=total_bytes)

    def _resolve_destination(self, category: str) -> Path:
        mapped = self.category_mapping.get(category) or category
        mapped_path = Path(mapped)
        if mapped_path.is_absolute():
            return mapped_path
        return self.destination_root / mapped

    @staticmethod
    def _estimate_duration(size: int, same_volume: bool) -> float:
        base_speed = 120_000_000 if same_volume else 40_000_000
        seconds = size / base_speed if base_speed else 0
        return round(seconds * 1000, 3)


__all__ = ["Planner", "PlanResult"]
