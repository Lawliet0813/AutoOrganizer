"""Command line interface for AutoOrganizer."""
from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from .classifier import ClassificationEngine
from .file_mover import FileMover
from .file_scanner import FileScanner
from .logger import configure_logging, log_event
from .models import FileCandidate, FilterDecision, Plan, PlanItem, PlanSummary
from .planner import Planner
from .reports import generate_reports
from .system_filter import SystemFilter


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="autoorganizer", description="AutoOrganizer CLI")
    parser.add_argument("--log", type=Path, help="Path to log file", default=None)
    parser.add_argument("--log-level", default="INFO", help="Logging level (DEBUG, INFO, WARNING, ERROR)")
    subparsers = parser.add_subparsers(dest="command")

    dry_parser = subparsers.add_parser("dry-run", help="Perform a dry-run and generate plan.json")
    dry_parser.add_argument("sources", nargs="+", help="Source directories to scan")
    dry_parser.add_argument("--dst", required=True, help="Destination root directory")
    dry_parser.add_argument("--rules", required=True, type=Path, help="Classification rules JSON")
    dry_parser.add_argument("--plan", type=Path, default=Path("plan.json"), help="Output plan file")
    dry_parser.add_argument("--conflict-strategy", choices=["rename", "skip", "overwrite"], default="rename")
    dry_parser.add_argument("--report-dir", type=Path, default=Path("."), help="Directory for reports")

    run_parser = subparsers.add_parser("run", help="Execute a previously generated plan")
    run_parser.add_argument("--plan", required=True, type=Path, help="Plan JSON file")
    run_parser.add_argument("--rollback", type=Path, default=Path("rollback.json"), help="Rollback file path")
    run_parser.add_argument("--conflict-strategy", choices=["rename", "skip", "overwrite"], default="rename")
    run_parser.add_argument("--report-dir", type=Path, default=Path("."), help="Directory for reports")

    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return 1

    level = getattr(logging, str(args.log_level).upper(), logging.INFO)
    logger = configure_logging(args.log, level=level)

    if args.command == "dry-run":
        return _cmd_dry_run(args, logger)
    if args.command == "run":
        return _cmd_run(args, logger)

    parser.print_help()
    return 1


def _cmd_dry_run(args: argparse.Namespace, logger: logging.Logger) -> int:
    rules = _load_rules(args.rules)
    filter_whitelist = rules.get("whitelist", []) if isinstance(rules, dict) else []
    sensitive_keywords = rules.get("sensitive_keywords", []) if isinstance(rules, dict) else []

    system_filter = SystemFilter(whitelist=filter_whitelist, sensitive_keywords=sensitive_keywords)
    classifier = ClassificationEngine(rules)
    planner = Planner(
        scanner=FileScanner(logger=logger),
        system_filter=system_filter,
        classifier=classifier,
        logger=logger,
        conflict_strategy=args.conflict_strategy,
    )

    plan = planner.build_plan(args.sources, args.dst)
    planner.save_plan(plan, args.plan)
    generate_reports(plan, None, args.report_dir)

    log_event(
        logger,
        level=logging.INFO,
        action="cli.dry_run",
        message="Dry-run completed",
        extra={
            "plan": str(args.plan),
            "report_dir": str(args.report_dir),
            "planned": plan.summary.planned,
            "skipped": plan.summary.skipped,
        },
    )
    return 0


def _cmd_run(args: argparse.Namespace, logger: logging.Logger) -> int:
    plan = _load_plan(args.plan)
    mover = FileMover(logger=logger, conflict_strategy=args.conflict_strategy)
    summary = mover.execute_plan(plan.items, args.rollback)
    generate_reports(plan, summary, args.report_dir)
    log_event(
        logger,
        level=logging.INFO,
        action="cli.run",
        message="Run completed",
        extra={
            "plan": str(args.plan),
            "rollback": str(args.rollback),
            "processed": summary.processed,
            "succeeded": summary.succeeded,
            "skipped": summary.skipped,
            "failed": summary.failed,
        },
    )
    return 0 if summary.failed == 0 else 2


def _load_rules(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_plan(path: Path) -> Plan:
    raw = json.loads(path.read_text(encoding="utf-8"))
    items = [
        PlanItem(
            source=Path(item["source"]),
            destination=Path(item["destination"]),
            operation=item["operation"],
            same_volume=bool(item.get("same_volume", True)),
            size=int(item.get("size", 0)),
            conflict=bool(item.get("conflict", False)),
            estimated_ms=item.get("estimated_ms"),
            hash_digest=item.get("hash_digest"),
            category=item.get("category"),
            confidence=item.get("confidence"),
            rationale=item.get("rationale"),
            flags=set(item.get("flags", [])),
        )
        for item in raw.get("items", [])
    ]
    summary_data = raw.get("summary", {})
    summary = PlanSummary(
        total_candidates=int(summary_data.get("total_candidates", len(items))),
        planned=int(summary_data.get("planned", len(items))),
        skipped=int(summary_data.get("skipped", 0)),
        total_bytes=int(summary_data.get("total_bytes", 0)),
        categories=dict(summary_data.get("categories", {})),
    )
    skipped_entries = []
    for entry in raw.get("skipped", []):
        candidate = FileCandidate(
            path=Path(entry.get("path", "")),
            size=int(entry.get("size", 0)),
            modified_at=datetime.utcnow(),
        )
        skipped_entries.append(
            FilterDecision(
                candidate=candidate,
                should_skip=bool(entry.get("should_skip", True)),
                reason=entry.get("reason"),
                flags=set(entry.get("flags", [])),
            )
        )
    plan = Plan(
        sources=[str(src) for src in raw.get("sources", [])],
        destination_root=Path(raw.get("destination_root", ".")),
        items=items,
        skipped=skipped_entries,
        summary=summary,
        generated_at=_parse_datetime(raw.get("generated_at")),
    )
    return plan


def _parse_datetime(value: str | None) -> datetime:
    if not value:
        return datetime.utcnow()
    try:
        return datetime.fromisoformat(value.replace("Z", ""))
    except ValueError:
        return datetime.utcnow()


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
