"""Safe file moving helpers."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Optional

from .config import DuplicateStrategy, FileInfo


class FileMover:
    """Move files while respecting duplicate handling strategies."""

    def __init__(self, strategy: DuplicateStrategy) -> None:
        self.strategy = strategy

    def move(self, file_info: FileInfo, destination: Path) -> Optional[Path]:
        destination.mkdir(parents=True, exist_ok=True)
        target = destination / file_info.file_name

        if target.exists():
            if self.strategy == DuplicateStrategy.SKIP:
                return None
            if self.strategy == DuplicateStrategy.RENAME:
                target = self._generate_unique_name(destination, file_info.file_name)
            elif self.strategy == DuplicateStrategy.OVERWRITE:
                if target.is_file():
                    target.unlink()

        shutil.move(str(file_info.file_path), str(target))
        return target

    def transactional_move(self, file_info: FileInfo, destination: Path) -> Optional[Path]:
        marker = destination / ".temp_moving"
        destination.mkdir(parents=True, exist_ok=True)
        marker.touch(exist_ok=True)
        try:
            result = self.move(file_info, destination)
            return result
        finally:
            if marker.exists():
                marker.unlink()

    @staticmethod
    def _generate_unique_name(destination: Path, file_name: str) -> Path:
        base = Path(file_name)
        stem = base.stem
        suffix = base.suffix
        counter = 1
        candidate = destination / file_name
        while candidate.exists() and counter < 1000:
            candidate = destination / f"{stem}_{counter}{suffix}"
            counter += 1
        return candidate
