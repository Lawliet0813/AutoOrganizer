# Watcher Module

The watcher subsystem delivers realtime filesystem monitoring with macOS
FSEvents support and a cross-platform polling fallback. Events are merged and
debounced before being evaluated in a dry-run that predicts AutoOrganizer move
plans.

## Architecture Overview

- **Backends** – `RealtimeWatcher` automatically prefers the FSEvents backend on
  macOS. When unavailable, it falls back to a lightweight polling backend that
  scans watched paths at a configurable interval.
- **Event Queue** – `auto_organizer.watcher.event_queue.EventQueue` merges rapid
  successive events for the same path and prefers terminal states (for example,
  delete beats modify). Queue flushing happens automatically based on the batch
  interval or when the watcher stops.
- **Dry-run** – `auto_organizer.watcher.dryrun.generate_move_plan` consumes
  emitted events, classifies surviving files and emits `move_plan` entries with
  `path`, `predicted_category`, `target`, `confidence`, and `conflict` flags. A
  JSON helper (`render_move_plan_json`) serializes the dry-run preview.

## Usage

```python
from auto_organizer.realtime_watcher import RealtimeWatcher
from auto_organizer.watcher.dryrun import generate_move_plan, render_move_plan_json

pending_batches: list[list[FileSystemEvent]] = []

watcher = RealtimeWatcher(["~/Downloads"], callback=pending_batches.append)
watcher.start()
# ... allow events to accumulate ...
watcher.stop()

entries = generate_move_plan(
    pending_batches[-1],
    destination_root="~/Organized",
    category_mapping={"docs": "Documents"},
)
print(render_move_plan_json(entries))
```

## /review Summary

- Event queue merges duplicate events, prefers deletes/moves, and flushes via
  debounce-aware batching.
- Polling backend maintains parity with FSEvents behaviour for local testing.
- Dry-run output now surfaces move plans as JSON-ready dictionaries.
- Tests cover event queue merge semantics and dry-run predictions.
