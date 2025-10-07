"""Safe file movement strategies implementing the execution phase."""
from __future__ import annotations

import hashlib
import json
import logging
import os
from pathlib import Path
from typing import Iterable

from .logger import log_event
from .models import ExecutionSummary, PlanItem, RollbackStep

LOGGER_NAME = "auto_organizer.mover"
_BUFFER_SIZE = 1024 * 1024


class ConflictError(RuntimeError):
    """Raised when a conflict prevents executing a plan item."""


class VerificationError(RuntimeError):
    """Raised when SHA-256 verification fails."""


class FileMover:
    """Execute move or copy operations following safety rules."""

    def __init__(
        self,
        *,
        logger: logging.Logger | None = None,
        conflict_strategy: str = "rename",
    ) -> None:
        self.logger = logger or logging.getLogger(LOGGER_NAME)
        if conflict_strategy not in {"rename", "skip", "overwrite"}:
            raise ValueError("conflict_strategy must be rename/skip/overwrite")
        self.conflict_strategy = conflict_strategy

    # ------------------------------------------------------------------
    def execute_plan(
        self,
        plan_items: Iterable[PlanItem],
        rollback_path: Path,
    ) -> ExecutionSummary:
        """Execute all plan items and persist rollback instructions."""

        rollback_steps: list[RollbackStep] = []
        processed = 0
        succeeded = 0
        skipped = 0
        failed = 0
        bytes_processed = 0
        errors: list[str] = []

        for item in plan_items:
            processed += 1
            try:
                if item.flags and "conflict" in item.flags and self.conflict_strategy == "skip":
                    skipped += 1
                    log_event(
                        self.logger,
                        level=logging.WARNING,
                        action="move.skip",
                        message=f"Skipping {item.source} due to conflict flag",
                        extra={"destination": str(item.destination)},
                    )
                    continue

                step = self._execute_item(item)
                rollback_steps.append(step)
                succeeded += 1
                bytes_processed += item.size
            except ConflictError as exc:
                skipped += 1
                log_event(
                    self.logger,
                    level=logging.WARNING,
                    action="move.conflict",
                    message=str(exc),
                    extra={"source": str(item.source), "destination": str(item.destination)},
                )
            except Exception as exc:  # pragma: no cover - defensive
                failed += 1
                message = f"Failed to move {item.source}: {exc}"
                errors.append(message)
                log_event(
                    self.logger,
                    level=logging.ERROR,
                    action="move.error",
                    message=message,
                    extra={"source": str(item.source), "destination": str(item.destination)},
                )

        self._write_rollback(rollback_steps, rollback_path)

        return ExecutionSummary(
            processed=processed,
            succeeded=succeeded,
            skipped=skipped,
            failed=failed,
            bytes_processed=bytes_processed,
            errors=errors,
        )

    # ------------------------------------------------------------------
    def _execute_item(self, item: PlanItem) -> RollbackStep:
        destination = item.destination
        destination.parent.mkdir(parents=True, exist_ok=True)

        if destination.exists():
            if self.conflict_strategy == "skip":
                raise ConflictError(f"Destination already exists: {destination}")
            if self.conflict_strategy == "rename":
                destination = self._next_available(destination)
            elif self.conflict_strategy == "overwrite":
                log_event(
                    self.logger,
                    level=logging.INFO,
                    action="move.overwrite",
                    message=f"Overwriting {destination}",
                )

        if item.operation == "rename":
            actual_destination = destination
            self._atomic_rename(item.source, actual_destination)
            log_event(
                self.logger,
                level=logging.INFO,
                action="move.rename",
                message=f"Moved {item.source} -> {actual_destination}",
                bytes_processed=item.size,
            )
            return RollbackStep(
                source=actual_destination,
                destination=item.source,
                operation="rename",
            )

        if item.operation == "copy":
            actual_destination = destination
            digest = self._copy_with_verification(item.source, actual_destination)
            item.hash_digest = digest
            log_event(
                self.logger,
                level=logging.INFO,
                action="move.copy",
                message=f"Copied {item.source} -> {actual_destination}",
                bytes_processed=item.size,
                extra={"hash": digest},
            )
            self._delete_source(item.source)
            return RollbackStep(
                source=actual_destination,
                destination=item.source,
                operation="restore",
            )

        raise ValueError(f"Unsupported operation: {item.operation}")

    def _atomic_rename(self, source: Path, destination: Path) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        os.replace(source, destination)

    def _copy_with_verification(self, source: Path, destination: Path) -> str:
        temp_destination = destination.with_suffix(destination.suffix + ".ao_tmp")
        hasher = hashlib.sha256()
        with source.open("rb") as src, temp_destination.open("wb") as dst:
            while True:
                chunk = src.read(_BUFFER_SIZE)
                if not chunk:
                    break
                dst.write(chunk)
                hasher.update(chunk)
            dst.flush()
            os.fsync(dst.fileno())
        source_digest = hasher.hexdigest()
        dest_digest = self._sha256(temp_destination)
        if source_digest != dest_digest:
            temp_destination.unlink(missing_ok=True)
            raise VerificationError("SHA-256 mismatch after copy")
        os.replace(temp_destination, destination)
        return source_digest

    def _sha256(self, path: Path) -> str:
        hasher = hashlib.sha256()
        with path.open("rb") as fh:
            while True:
                chunk = fh.read(_BUFFER_SIZE)
                if not chunk:
                    break
                hasher.update(chunk)
        return hasher.hexdigest()

    def _delete_source(self, source: Path) -> None:
        source.unlink()

    def _next_available(self, destination: Path) -> Path:
        suffix = 1
        candidate = destination
        while candidate.exists():
            candidate = destination.with_name(f"{destination.stem} ({suffix}){destination.suffix}")
            suffix += 1
        return candidate

    def _write_rollback(self, steps: list[RollbackStep], rollback_path: Path) -> None:
        data = [
            {"operation": step.operation, "from": str(step.source), "to": str(step.destination)}
            for step in steps
        ]
        rollback_path.parent.mkdir(parents=True, exist_ok=True)
        rollback_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

        script_path = rollback_path.with_suffix(".sh")
        lines = ["#!/bin/sh", "set -euo pipefail"]
        for step in steps:
            if step.operation == "rename":
                lines.append(f"mv \"{step.source}\" \"{step.destination}\"")
            elif step.operation == "restore":
                lines.append(f"cp -p \"{step.source}\" \"{step.destination}\"")
        script_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        script_path.chmod(0o755)


__all__ = ["FileMover", "ConflictError", "VerificationError"]
