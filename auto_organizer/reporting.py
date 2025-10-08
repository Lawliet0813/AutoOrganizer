"""Rendering helpers for AutoOrganizer reports."""
from __future__ import annotations

import json
from typing import Mapping


def render_report(raw: Mapping[str, object], fmt: str) -> str:
    """Render a normalized report payload according to *fmt*.

    ``fmt`` accepts ``"text"``, ``"markdown"`` or ``"json"``.
    """

    fmt = fmt.lower()
    if fmt == "json":
        payload = dict(raw)
        payload.setdefault("version", "1.0")
        return json.dumps(payload, indent=2, ensure_ascii=False)

    totals = raw.get("totals", {}) if isinstance(raw, Mapping) else {}
    classification = raw.get("classification", {}) if isinstance(raw, Mapping) else {}

    if fmt == "markdown":
        lines = [
            "# AutoOrganizer Report",
            "",
            "## Summary",
            f"- Processed files: {totals.get('processed', 0)}",
            f"- Moved files: {totals.get('moved', 0)}",
            f"- Skipped files: {totals.get('skipped', 0)}",
            f"- Errors: {totals.get('errors', 0)}",
            "",
            "## Classification",
        ]
        if classification:
            lines.append("| Category | Count |")
            lines.append("| --- | --- |")
            for key, value in sorted(classification.items()):
                lines.append(f"| {key} | {value} |")
        else:
            lines.append("(no classification data)")
        return "\n".join(lines)

    lines = [
        "AutoOrganizer Report",
        "====================",
        f"Processed: {totals.get('processed', 0)}",
        f"Moved: {totals.get('moved', 0)}",
        f"Skipped: {totals.get('skipped', 0)}",
        f"Errors: {totals.get('errors', 0)}",
        "",
        "Classification:",
    ]
    if classification:
        for key, value in sorted(classification.items()):
            lines.append(f"  - {key}: {value}")
    else:
        lines.append("  (no data)")
    return "\n".join(lines)


__all__ = ["render_report"]
