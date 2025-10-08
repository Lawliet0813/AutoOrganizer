"""Safe file movement strategies."""
from __future__ import annotations

import hashlib
import logging
import shutil
from pathlib import Path

from .logger import log_event
from .models import PlanItem


def _calculate_sha256(file_path: Path) -> str:
    """Calculate the SHA256 hash of a file."""
    sha256 = hashlib.sha256()
    with file_path.open("rb") as f:
        while chunk := f.read(8192):
            sha256.update(chunk)
    return sha256.hexdigest()


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
        """Copy a file and verify its integrity, then delete the source."""
        source = Path(plan_item.source)
        destination = plan_item.destination
        destination.parent.mkdir(parents=True, exist_ok=True)

        try:
            # 1. Copy the file
            shutil.copy2(source, destination)

            # 2. Verify the copy by comparing hashes
            source_hash = _calculate_sha256(source)
            dest_hash = _calculate_sha256(destination)

            if source_hash == dest_hash:
                # 3. Hashes match, delete the source file
                source.unlink()
                log_event(
                    self.logger,
                    level=logging.INFO,
                    action="move.copy_and_verify",
                    message=f"Moved cross-volume {source} -> {destination}",
                    bytes_processed=plan_item.size,
                )
            else:
                # 4. Hashes mismatch, log an error and delete the corrupted destination file
                destination.unlink()  # Clean up the invalid copy
                log_event(
                    self.logger,
                    level=logging.ERROR,
                    action="move.copy_failed_verification",
                    message=f"Verification failed for {source}. Hashes do not match. Destination file removed.",
                    bytes_processed=plan_item.size,
                )
                raise IOError(f"SHA-256 verification failed for {source}")

        except (IOError, OSError) as e:
            log_event(
                self.logger,
                level=logging.ERROR,
                action="move.copy_error",
                message=f"Error moving {source} to {destination}: {e}",
                bytes_processed=plan_item.size,
            )
            # Attempt to clean up a partially copied file if it exists
            if destination.exists():
                destination.unlink()
            raise
