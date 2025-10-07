"""Safe file movement strategies."""
from __future__ import annotations

import logging
import shutil
from pathlib import Path

from .logger import log_event
from .models import PlanItem


class FileMover:
    """Execute move or copy operations following safety rules."""

    def __init__(self, logger: logging.Logger) -> None:
        self.logger = logger

    def execute(self, plan_item: PlanItem) -> None:
        """Execute a :class:`PlanItem`. Currently implements atomic rename and copy."""

        if plan_item.operation == "rename":
            self._rename(plan_item)
        elif plan_item.operation == "copy":
            self._copy(plan_item)
        else:
            raise ValueError(f"Unsupported operation: {plan_item.operation}")

    def _rename(self, plan_item: PlanItem) -> None:
        destination = plan_item.destination
        destination.parent.mkdir(parents=True, exist_ok=True)
        Path(plan_item.source).rename(destination)
        log_event(
            self.logger,
            level=logging.INFO,
            action="move.rename",
            message=f"Moved {plan_item.source} -> {destination}",
            bytes_processed=plan_item.size,
        )

    def _copy(self, plan_item: PlanItem) -> None:
        destination = plan_item.destination
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(plan_item.source, destination)
        log_event(
            self.logger,
            level=logging.INFO,
            action="move.copy",
            message=f"Copied {plan_item.source} -> {destination}",
            bytes_processed=plan_item.size,
        )
