"""Planner component responsible for dry-run plan generation."""
from __future__ import annotations

import json
import logging
from collections import Counter
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Sequence

from .classifier import ClassificationEngine
from .file_scanner import FileScanner
from .logger import log_event
from .models import (
    ClassificationResult,
    FileCandidate,
    FilterDecision,
    Plan,
    PlanItem,
    PlanSummary,
)
from .system_filter import SystemFilter

LOGGER_NAME = "auto_organizer.planner"
_DEFAULT_THROUGHPUT = 50 * 1024 * 1024  # 50 MB/s optimistic dry-run estimation


class Planner:
    """Aggregate scanner, filter and classifier to produce a plan."""

    def __init__(
        self,
        *,
        scanner: FileScanner | None = None,
        system_filter: SystemFilter | None = None,
        classifier: ClassificationEngine | None = None,
        logger: logging.Logger | None = None,
        throughput_bytes_per_sec: int = _DEFAULT_THROUGHPUT,
        conflict_strategy: str = "rename",
    ) -> None:
        self.scanner = scanner or FileScanner()
        self.filter = system_filter or SystemFilter()
        self.classifier = classifier or ClassificationEngine()
        self.logger = logger or logging.getLogger(LOGGER_NAME)
        self.throughput = max(1, throughput_bytes_per_sec)
        if conflict_strategy not in {"rename", "skip", "overwrite"}:
            raise ValueError("conflict_strategy must be rename/skip/overwrite")
        self.conflict_strategy = conflict_strategy

    # ------------------------------------------------------------------
    # Public API
    def build_plan(self, sources: Sequence[str | Path], destination_root: str | Path) -> Plan:
        """Perform a dry-run, returning a :class:`~auto_organizer.models.Plan`."""

        scan_result = self.scanner.scan(sources)
        decisions = list(self.filter.iter_decisions(scan_result.candidates))
        planned_items: list[PlanItem] = []
        skipped: list[FilterDecision] = []
        categories: Counter[str] = Counter()
        total_bytes = 0

        dest_root_path = Path(destination_root).expanduser().resolve()

        for decision in decisions:
            if decision.should_skip:
                skipped.append(decision)
                log_event(
                    self.logger,
                    level=logging.INFO,
                    action="plan.skip",
                    message=f"Skip {decision.candidate.path}",
                    extra={
                        "path": str(decision.candidate.path),
                        "reason": decision.reason,
                        "flags": sorted(decision.flags),
                    },
                )
                continue

            classification = self.classifier.classify(decision.candidate)
            destination = self._resolve_destination(dest_root_path, decision.candidate, classification)
            final_destination, conflict_detected, skipped_due_to_conflict = self._handle_conflict(destination)
            if skipped_due_to_conflict:
                skipped.append(
                    FilterDecision(
                        candidate=decision.candidate,
                        should_skip=True,
                        reason="conflict",
                        flags={"conflict"},
                    )
                )
                continue

            same_volume = self._same_volume(decision.candidate.path, final_destination)
            operation = "rename" if same_volume else "copy"
            estimated_ms = (decision.candidate.size / self.throughput) * 1000.0
            total_bytes += decision.candidate.size

            plan_item = PlanItem(
                source=decision.candidate.path,
                destination=final_destination,
                operation=operation,
                same_volume=same_volume,
                size=decision.candidate.size,
                conflict=conflict_detected,
                estimated_ms=estimated_ms,
                category=classification.category,
                confidence=classification.confidence,
                rationale=classification.rationale,
                flags=decision.flags,
            )
            planned_items.append(plan_item)
            categories[classification.category] += 1

            log_event(
                self.logger,
                level=logging.INFO,
                action="plan.item",
                message=f"Planned {decision.candidate.path} -> {final_destination}",
                extra={
                    "operation": operation,
                    "category": classification.category,
                    "confidence": classification.confidence,
                    "conflict": conflict_detected,
                },
            )

        summary = PlanSummary(
            total_candidates=len(decisions),
            planned=len(planned_items),
            skipped=len(skipped),
            total_bytes=total_bytes,
            categories=dict(categories),
        )

        plan = Plan(
            sources=[str(Path(src).expanduser()) for src in sources],
            destination_root=dest_root_path,
            items=planned_items,
            skipped=skipped,
            summary=summary,
            generated_at=datetime.utcnow(),
        )
        return plan

    def save_plan(self, plan: Plan, path: str | Path) -> None:
        """Persist plan information as JSON."""

        payload = self._plan_to_dict(plan)
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    # ------------------------------------------------------------------
    # Helpers
    def _plan_to_dict(self, plan: Plan) -> dict[str, object]:
        return {
            "generated_at": plan.generated_at.isoformat(timespec="seconds") + "Z",
            "sources": list(plan.sources),
            "destination_root": str(plan.destination_root),
            "summary": {
                "total_candidates": plan.summary.total_candidates,
                "planned": plan.summary.planned,
                "skipped": plan.summary.skipped,
                "total_bytes": plan.summary.total_bytes,
                "categories": plan.summary.categories,
            },
            "items": [self._plan_item_to_dict(item) for item in plan.items],
            "skipped": [decision.to_dict() for decision in plan.skipped],
        }

    def _plan_item_to_dict(self, item: PlanItem) -> dict[str, object]:
        payload = asdict(item)
        payload["source"] = str(item.source)
        payload["destination"] = str(item.destination)
        payload["flags"] = sorted(item.flags)
        return payload

    def _resolve_destination(
        self,
        destination_root: Path,
        candidate: FileCandidate,
        classification: ClassificationResult,
    ) -> Path:
        rules = self.classifier.rules if isinstance(self.classifier.rules, dict) else {}
        destinations = rules.get("destinations", {}) if isinstance(rules, dict) else {}
        default_destination = rules.get("default_destination", "uncategorized") if isinstance(rules, dict) else "uncategorized"
        sub_dir = destinations.get(classification.category, default_destination)
        return destination_root.joinpath(sub_dir, candidate.path.name)

    def _handle_conflict(self, destination: Path) -> tuple[Path, bool, bool]:
        conflict = destination.exists()
        if not conflict:
            return destination, False, False

        if self.conflict_strategy == "overwrite":
            return destination, True, False

        if self.conflict_strategy == "skip":
            return destination, True, True

        # rename strategy
        suffix = 1
        candidate = destination
        stem = destination.stem
        suffix_template = "{} ({}){}"
        while candidate.exists():
            candidate = destination.with_name(suffix_template.format(stem, suffix, destination.suffix))
            suffix += 1
        return candidate, True, False

    def _same_volume(self, source: Path, destination: Path) -> bool:
        try:
            src_dev = source.stat().st_dev
        except FileNotFoundError:
            return False

        target_parent = destination.parent
        while not target_parent.exists() and target_parent != target_parent.parent:
            target_parent = target_parent.parent

        try:
            dest_dev = target_parent.stat().st_dev
        except FileNotFoundError:
            return False
        return src_dev == dest_dev


__all__ = ["Planner"]
