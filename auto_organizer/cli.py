"""Command line interface for AutoOrganizer."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from .dedup_index import DedupIndex
from .logger import configure_logging, next_log_path
from .reporter import ReportGenerator, RunSummary
from .rollback import RollbackManager
from .rules import apply as apply_rules
from .rules import preview as preview_rules
from .rules import RulesValidationError, upgrade_rules, validate_rules
from .reporting import render_report
from .scheduler import build_schedule, launch_agent_payload, write_launch_agent


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "handler"):
        parser.print_help()
        return 1
    return args.handler(args)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="autoorganizer", description="AutoOrganizer CLI")
    subparsers = parser.add_subparsers(dest="command")

    # dedup subcommands
    dedup_parser = subparsers.add_parser("dedup", help="Deduplication utilities")
    dedup_sub = dedup_parser.add_subparsers(dest="dedup_command")

    dedup_report = dedup_sub.add_parser("report", help="Generate deduplication report")
    dedup_report.add_argument("paths", nargs="*", help="Paths to index before reporting")
    dedup_report.add_argument("--db", type=Path, help="Path to dedup SQLite database")
    dedup_report.add_argument("--output", type=Path, default=Path("reports"))
    dedup_report.set_defaults(handler=_handle_dedup_report)

    dedup_clean = dedup_sub.add_parser("clean", help="Remove duplicate files")
    dedup_clean.add_argument("paths", nargs="*", help="Paths to index before cleaning")
    dedup_clean.add_argument("--db", type=Path)
    dedup_clean.add_argument("--dry-run", action="store_true")
    dedup_clean.set_defaults(handler=_handle_dedup_clean)

    # rollback command
    rollback = subparsers.add_parser("rollback", help="Restore files based on rollback.json")
    rollback.add_argument("rollback_file", type=Path)
    rollback.add_argument("--filter", nargs="*", default=None, help="Filter by substring")
    rollback.add_argument("--dry-run", action="store_true")
    rollback.set_defaults(handler=_handle_rollback)

    # rules commands
    rules_parser = subparsers.add_parser("rules", help="Rules management")
    rules_sub = rules_parser.add_subparsers(dest="rules_command")

    rules_validate = rules_sub.add_parser("validate", help="Validate a rules file")
    rules_validate.add_argument("rules_file", type=Path)
    rules_validate.set_defaults(handler=_handle_rules_validate)

    rules_upgrade = rules_sub.add_parser("upgrade", help="Upgrade a rules file to the latest schema")
    rules_upgrade.add_argument("rules_file", type=Path)
    rules_upgrade.add_argument("--output", type=Path)
    rules_upgrade.set_defaults(handler=_handle_rules_upgrade)

    rules_preview = rules_sub.add_parser("preview", help="Preview how files would be organized")
    rules_preview.add_argument("--config", type=Path, required=True)
    rules_preview.add_argument("--source", type=Path, action="append", required=True)
    rules_preview.add_argument("--target", type=Path, required=True)
    rules_preview.add_argument("--limit", type=int)
    rules_preview.add_argument("--output", type=Path)
    rules_preview.set_defaults(handler=_handle_rules_preview)

    rules_apply = rules_sub.add_parser("apply", help="Apply rules to organize files")
    rules_apply.add_argument("--config", type=Path, required=True)
    rules_apply.add_argument("--source", type=Path, action="append", required=True)
    rules_apply.add_argument("--target", type=Path, required=True)
    rules_apply.add_argument("--limit", type=int)
    rules_apply.add_argument("--output", type=Path)
    rules_apply.add_argument(
        "--rollback", type=Path, help="Path to write rollback information (default target/rollback.json)"
    )
    rules_apply.add_argument("--dry-run", action="store_true", help="Run without moving files")
    rules_apply.set_defaults(handler=_handle_rules_apply)

    # report command
    report_parser = subparsers.add_parser("report", help="Generate consolidated reports")
    report_parser.add_argument("summary", type=Path, help="Path to run summary JSON")
    report_parser.add_argument("--format", choices=["text", "markdown", "json"], default="text")
    report_parser.add_argument("--output", type=Path)
    report_parser.set_defaults(handler=_handle_report)

    # schedule command
    schedule_parser = subparsers.add_parser("schedule", help="Generate LaunchAgent configuration")
    schedule_parser.add_argument("--mode", choices=["quick", "full", "deep"], default="quick")
    schedule_parser.add_argument("--scan-path", nargs="+", default=[str(Path.home() / "Downloads")])
    schedule_parser.add_argument(
        "--output", type=Path, default=Path.home() / "Library/LaunchAgents/com.autoorganizer.agent.plist"
    )
    schedule_parser.add_argument("--executable", default="autoorganizer")
    schedule_parser.set_defaults(handler=_handle_schedule)

    return parser


def _handle_dedup_report(args: argparse.Namespace) -> int:
    index = DedupIndex(args.db) if args.db else DedupIndex()
    try:
        if args.paths:
            index.index_paths(args.paths)
        duplicates = index.get_duplicates()
        if not duplicates:
            print("No duplicates found.")
            return 0
        json_path, txt_path = index.write_reports(duplicates, args.output)
        print(f"Report written to {json_path} and {txt_path}")
        return 0
    finally:
        index.close()


def _handle_dedup_clean(args: argparse.Namespace) -> int:
    index = DedupIndex(args.db) if args.db else DedupIndex()
    try:
        if args.paths:
            index.index_paths(args.paths)
        deletions = index.clean_duplicates(dry_run=args.dry_run)
        if not deletions:
            print("No duplicates to clean.")
            return 0
        for record, keeper in deletions:
            action = "Would remove" if args.dry_run else "Removed"
            print(f"{action} {record.path} (keeping {keeper})")
        return 0
    finally:
        index.close()


def _handle_rollback(args: argparse.Namespace) -> int:
    log_path = next_log_path("rollback")
    logger = configure_logging(log_path)
    manager = RollbackManager(logger)
    entries = manager.load_entries(args.rollback_file)
    restored = manager.restore(entries, dry_run=args.dry_run, target_filter=args.filter)
    print(f"Restored {len(restored)} file(s). Log: {log_path}")
    return 0


def _handle_rules_validate(args: argparse.Namespace) -> int:
    try:
        validate_rules(args.rules_file)
    except RulesValidationError as exc:
        print(f"Validation failed: {exc}", file=sys.stderr)
        return 1
    else:
        print("Rules file is valid.")
        return 0


def _handle_rules_upgrade(args: argparse.Namespace) -> int:
    upgraded = upgrade_rules(args.rules_file, output=args.output)
    destination = args.output if args.output else args.rules_file
    print(f"Upgraded rules written to {destination}. Version: {upgraded['version']}")
    return 0


def _handle_rules_preview(args: argparse.Namespace) -> int:
    logger = configure_logging()
    sources = args.source
    try:
        return preview_rules(
            config=args.config,
            sources=sources,
            target=args.target,
            limit=args.limit,
            output=args.output,
        )
    except RulesValidationError as exc:
        logger.error("Preview failed: %s", exc)
        print(f"Preview failed: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("Unexpected preview error: %s", exc)
        print(f"Preview failed: {exc}", file=sys.stderr)
        return 1


def _handle_rules_apply(args: argparse.Namespace) -> int:
    logger = configure_logging()
    sources = args.source
    try:
        return apply_rules(
            config=args.config,
            sources=sources,
            target=args.target,
            limit=args.limit,
            output=args.output,
            rollback=args.rollback,
            dry_run=args.dry_run,
        )
    except RulesValidationError as exc:
        logger.error("Apply failed: %s", exc)
        print(f"Apply failed: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("Unexpected apply error: %s", exc)
        print(f"Apply failed: {exc}", file=sys.stderr)
        return 1


def _handle_report(args: argparse.Namespace) -> int:
    try:
        raw = json.loads(args.summary.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(f"Summary file not found: {args.summary}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as exc:
        print(f"Invalid summary JSON: {exc}", file=sys.stderr)
        return 1
    summary = RunSummary(
        started_at=datetime.fromisoformat(raw["started_at"]),
        finished_at=datetime.fromisoformat(raw["finished_at"]),
        classification_counts=raw.get("classification", {}),
        moved_files=raw.get("moved_files", 0),
        skipped_files=raw.get("skipped_files", 0),
        reclaimed_bytes=raw.get("reclaimed_bytes", 0),
        errors=raw.get("errors", []),
    )
    generator = ReportGenerator()
    payload = generator.build_payload(summary)
    rendered = render_report(payload, args.format)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
        print(f"Report written to {args.output}")
    else:
        print(rendered)
    return 0


def _handle_schedule(args: argparse.Namespace) -> int:
    plan = build_schedule(args.mode, args.scan_path)
    payload = launch_agent_payload(plan, args.executable)
    destination = write_launch_agent(payload, args.output)
    print(
        "LaunchAgent created at",
        destination,
        "interval(min) =",
        plan.interval_minutes,
        "window =",
        plan.suggested_window,
        "log =",
        plan.log_path,
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
