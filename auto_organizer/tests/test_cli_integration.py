from __future__ import annotations

import json
from pathlib import Path

from auto_organizer.cli import main


def test_dry_run_then_run(tmp_path: Path) -> None:
    source_dir = tmp_path / "source"
    destination_root = tmp_path / "dest"
    source_dir.mkdir()
    destination_root.mkdir()
    file_path = source_dir / "notes.txt"
    file_path.write_text("hello world", encoding="utf-8")

    rules = {
        "classification": {
            "extension": {".txt": "text"},
        },
        "destinations": {"text": "Text", "misc": "Misc"},
        "default_destination": "Misc",
        "default_category": "misc",
    }
    rules_path = tmp_path / "rules.json"
    rules_path.write_text(json.dumps(rules), encoding="utf-8")

    plan_path = tmp_path / "plan.json"
    report_dir = tmp_path / "reports"

    exit_code = main(
        [
            "dry-run",
            str(source_dir),
            "--dst",
            str(destination_root),
            "--rules",
            str(rules_path),
            "--plan",
            str(plan_path),
            "--report-dir",
            str(report_dir),
        ]
    )
    assert exit_code == 0
    assert plan_path.exists()
    plan_data = json.loads(plan_path.read_text(encoding="utf-8"))
    assert plan_data["summary"]["planned"] == 1

    rollback_path = tmp_path / "rollback.json"
    exit_code_run = main(
        [
            "run",
            "--plan",
            str(plan_path),
            "--rollback",
            str(rollback_path),
            "--report-dir",
            str(report_dir),
        ]
    )
    assert exit_code_run == 0
    moved_path = destination_root / "Text" / "notes.txt"
    assert moved_path.exists()
    assert not file_path.exists()
    report_json = report_dir / "report.json"
    report_txt = report_dir / "report.txt"
    assert report_json.exists()
    assert report_txt.exists()
    rollback_data = json.loads(rollback_path.read_text(encoding="utf-8"))
    assert rollback_data[0]["operation"] in {"rename", "restore"}
