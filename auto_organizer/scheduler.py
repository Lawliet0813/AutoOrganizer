"""Helpers for generating LaunchAgent schedules."""
from __future__ import annotations

import os
import plistlib
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .logger import next_log_path


@dataclass(slots=True)
class SchedulePlan:
    mode: str
    interval_minutes: int
    suggested_window: str
    log_path: Path
    file_count: int
    free_space_ratio: float


def analyse_directory(paths: Iterable[str | Path]) -> tuple[int, float]:
    total_files = 0
    free_ratio = 0.5
    for raw_path in paths:
        path = Path(raw_path).expanduser()
        if path.exists():
            if path.is_dir():
                for _, _, files in os.walk(path):
                    total_files += len(files)
            elif path.is_file():
                total_files += 1
            usage = shutil.disk_usage(path if path.is_dir() else path.parent)
            free_ratio = usage.free / usage.total if usage.total else 0.0
            break
    return total_files, free_ratio


def build_schedule(mode: str, scan_paths: Iterable[str | Path]) -> SchedulePlan:
    file_count, free_ratio = analyse_directory(scan_paths)
    if mode == "quick":
        interval = 30 if file_count > 2000 else 60
    elif mode == "full":
        interval = 6 * 60 if file_count > 5000 else 12 * 60
    else:  # deep
        interval = 7 * 24 * 60

    window = "22:00-06:00" if free_ratio < 0.25 else "18:00-23:00"
    log_path = next_log_path(f"schedule-{mode}")
    return SchedulePlan(
        mode=mode,
        interval_minutes=interval,
        suggested_window=window,
        log_path=log_path,
        file_count=file_count,
        free_space_ratio=free_ratio,
    )


def launch_agent_payload(plan: SchedulePlan, executable: str) -> dict:
    return {
        "Label": "com.autoorganizer.agent",
        "ProgramArguments": [executable, "run", f"--mode={plan.mode}"],
        "StartInterval": plan.interval_minutes * 60,
        "StandardOutPath": str(plan.log_path),
        "StandardErrorPath": str(plan.log_path),
    }


def write_launch_agent(payload: dict, destination: str | Path) -> Path:
    destination_path = Path(destination)
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    with destination_path.open("wb") as handle:
        plistlib.dump(payload, handle)
    return destination_path


__all__ = [
    "SchedulePlan",
    "analyse_directory",
    "build_schedule",
    "launch_agent_payload",
    "write_launch_agent",
]
