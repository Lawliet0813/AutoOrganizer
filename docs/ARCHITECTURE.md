# AutoOrganizer Architecture (Phase 2)

## Overview

AutoOrganizer is organised into modular services that can be composed by the CLI
or higher level automation. Phase 2 introduces deduplication, reporting,
rollback, rules management, and scheduler coordination.

```
CLI (`autoorganizer`)
 ├─ Deduplication (`DedupIndex`)
 ├─ Planner / Reporter
 ├─ Rollback manager
 ├─ Rules validation & upgrade
 └─ Scheduler / LaunchAgent generator
```

### Core Data Flow

1. **Scanning** – `FileScanner` produces `FileCandidate` objects that travel
   through the `SystemFilter` and `ClassificationEngine`.
2. **Planning** – `Planner` converts candidates into `PlanItem` entries. Each
   entry contains source/destination metadata, volume hints, estimates and
   conflict flags.
3. **Execution** – `FileMover` executes plan items while emitting structured
   logs via `logger.log_event`.
4. **Reporting** – `ReportGenerator` consumes a `RunSummary` to consolidate
   statistics, timings, classification counts, reclaimed bytes and error
   snapshots. Reports are emitted as both JSON and text.
5. **Deduplication** – `DedupIndex` maintains a SQLite backed SHA-256 index.
   It can purge missing entries, create reports, and clean redundant files while
   retaining the oldest copy per hash.
6. **Rollback** – `RollbackManager` reads `rollback.json`, verifies SHA-256, and
   restores backups safely with audit logging.
7. **Rules** – `rules.py` validates rules against
   `auto_organizer/rules.schema.json`, upgrades legacy versions, and highlights
   schema or syntax issues with file/line hints.
8. **Scheduler** – `scheduler.py` analyses target folders, estimates workloads,
   and emits LaunchAgent payloads with recommended intervals and log paths.

## Logging & Telemetry

`logger.configure_logging` ensures a single structured logger. `next_log_path`
provides timestamped log files under `~/.autoorganizer/logs`, rotating files
above 5 MB. All modules reuse `log_event` to output JSON-line logs.

## Reporting Contract

`RunSummary` encapsulates execution stats:

```python
RunSummary(
    started_at=datetime,
    finished_at=datetime,
    classification_counts={...},
    moved_files=int,
    skipped_files=int,
    reclaimed_bytes=int,
    errors=[{"path": str, "message": str}, ...],
)
```

`ReportGenerator.build_payload` normalises the structure and `write` emits
`report.json` & `report.txt` for downstream consumption or auditing.

## Deduplication Schema

`dedup_index` uses SQLite table `dedup_index(hash, path, size, modified_at)`.
Indexes are created on the `hash` column to speed up grouping. Reports include
total reclaimed bytes estimates and plain-text summaries for operators.

## Scheduler Modes

- **quick** – 30–60 minute intervals for lightweight runs.
- **full** – 6–12 hour intervals, depending on file counts.
- **deep** – weekly scans for archival clean-up.

Intervals adjust automatically based on file volume, while execution windows are
selected using disk pressure heuristics (`22:00-06:00` if free space <25%).

## Future Work (Phase 3 Preview)

- GUI dashboard leveraging the Reporter outputs.
- Real-time filesystem monitoring with watch services.
- Machine-learning classification enrichment with feedback loop.
