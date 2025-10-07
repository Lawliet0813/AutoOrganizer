"""Reporting helpers for dry-run and execution phases."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from .models import ExecutionSummary, Plan


def generate_reports(plan: Plan, execution: ExecutionSummary | None, output_dir: Path) -> None:
    """Generate ``report.json`` and ``report.txt`` files."""

    output_dir.mkdir(parents=True, exist_ok=True)
    report_json = _build_json(plan, execution)
    (output_dir / "report.json").write_text(json.dumps(report_json, indent=2, ensure_ascii=False), encoding="utf-8")
    (output_dir / "report.txt").write_text(_build_text(report_json), encoding="utf-8")


def _build_json(plan: Plan, execution: ExecutionSummary | None) -> dict[str, object]:
    payload: dict[str, object] = {
        "generated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "plan": {
            "sources": list(plan.sources),
            "destination_root": str(plan.destination_root),
            "summary": {
                "total_candidates": plan.summary.total_candidates,
                "planned": plan.summary.planned,
                "skipped": plan.summary.skipped,
                "total_bytes": plan.summary.total_bytes,
                "categories": plan.summary.categories,
            },
            "skipped": [decision.to_dict() for decision in plan.skipped],
        },
    }
    if execution:
        payload["execution"] = {
            "processed": execution.processed,
            "succeeded": execution.succeeded,
            "skipped": execution.skipped,
            "failed": execution.failed,
            "bytes_processed": execution.bytes_processed,
            "errors": execution.errors,
        }
    return payload


def _build_text(payload: dict[str, object]) -> str:
    plan_section = payload["plan"]
    summary = plan_section["summary"]
    lines = [
        "AutoOrganizer Execution Report",
        "================================",
        f"Report generated: {payload['generated_at']}",
        "",
        "Plan Summary:",
        f"  Sources       : {', '.join(plan_section['sources'])}",
        f"  Destination   : {plan_section['destination_root']}",
        f"  Candidates    : {summary['total_candidates']}",
        f"  Planned       : {summary['planned']}",
        f"  Skipped       : {summary['skipped']}",
        f"  Total bytes   : {summary['total_bytes']}",
    ]
    categories = summary.get("categories", {})
    if categories:
        lines.append("  Categories    :")
        for category, count in sorted(categories.items()):
            lines.append(f"    - {category}: {count}")
    skipped = plan_section.get("skipped", [])
    if skipped:
        lines.append("")
        lines.append("Skipped Items:")
        for entry in skipped[:10]:
            lines.append(f"  - {entry['path']} ({entry.get('reason', 'unknown')})")
        if len(skipped) > 10:
            lines.append(f"    ... {len(skipped) - 10} more")
    execution = payload.get("execution")
    if execution:
        lines.extend(
            [
                "",
                "Execution Summary:",
                f"  Processed     : {execution['processed']}",
                f"  Succeeded     : {execution['succeeded']}",
                f"  Skipped       : {execution['skipped']}",
                f"  Failed        : {execution['failed']}",
                f"  Bytes moved   : {execution['bytes_processed']}",
            ]
        )
        errors = execution.get("errors", [])
        if errors:
            lines.append("  Errors:")
            for err in errors:
                lines.append(f"    - {err}")
    lines.append("")
    return "\n".join(lines)


__all__ = ["generate_reports"]
