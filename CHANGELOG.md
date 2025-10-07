# Changelog

## [0.2.0] - 2024-05-12

### Added
- SQLite backed deduplication index with `dedup report` / `dedup clean` CLI commands.
- Unified report generator producing `report.json` and `report.txt`.
- Rollback manager restoring files from `rollback.json` with SHA-256 verification.
- Rules schema validation (`rules validate`) and migration support (`rules upgrade`).
- LaunchAgent scheduler helper with quick/full/deep modes and log provisioning.
- New tests covering deduplication, reporting, rules, and scheduler integrations.
- Documentation refresh describing Phase 2 architecture.

### Changed
- Logger now rotates files over 5 MB and provides timestamped paths.
- Planner produces enriched plan items with estimates and conflict detection.

### Fixed
- Rules validation now reports human friendly line/column information.
