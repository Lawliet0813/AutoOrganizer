"""AutoOrganizer package exports."""

from .cli import main as cli_main
from .realtime_watcher import EventType, FileSystemEvent, RealtimeWatcher

__all__ = [
    "cli_main",
    "EventType",
    "FileSystemEvent",
    "RealtimeWatcher",
]
