from __future__ import annotations

import json
from datetime import datetime, timedelta

from auto_organizer import cli
from auto_organizer.rules import CURRENT_RULES_VERSION


def test_cli_dedup_and_report(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    dup1 = tmp_path / "dup1.txt"
    dup2 = tmp_path / "dup2.txt"
    dup1.write_text("same", encoding="utf-8")
    dup2.write_text("same", encoding="utf-8")

    exit_code = cli.main(["dedup", "report", str(tmp_path)])
    assert exit_code == 0
    output = capsys.readouterr().out
    assert "Report written" in output

    summary_path = tmp_path / "summary.json"
    summary_path.write_text(
        json.dumps(
            {
                "started_at": datetime.now().isoformat(),
                "finished_at": (datetime.now() + timedelta(seconds=2)).isoformat(),
                "classification": {"docs": 2},
                "moved_files": 1,
                "skipped_files": 1,
                "reclaimed_bytes": 100,
                "errors": [],
            }
        ),
        encoding="utf-8",
    )

    exit_code = cli.main(["report", str(summary_path), "--output", str(tmp_path / "reports")])
    assert exit_code == 0


def test_cli_rules_and_schedule(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    rules_path = tmp_path / "rules.json"
    rules_path.write_text(
        json.dumps({"version": CURRENT_RULES_VERSION, "rules": {"docs": {"extensions": [".txt"]}}}),
        encoding="utf-8",
    )

    exit_code = cli.main(["rules", "validate", str(rules_path)])
    assert exit_code == 0

    legacy = tmp_path / "legacy.json"
    legacy.write_text(json.dumps({"version": "1.0", "categories": {"docs": [".txt"]}}), encoding="utf-8")
    exit_code = cli.main(["rules", "upgrade", str(legacy), "--output", str(tmp_path / "upgraded.json")])
    assert exit_code == 0

    exit_code = cli.main(["schedule", "--mode", "quick", "--scan-path", str(tmp_path), "--output", str(tmp_path / "agent.plist")])
    assert exit_code == 0
    assert (tmp_path / "agent.plist").exists()


def test_cli_rollback(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    backup = tmp_path / "backup.txt"
    backup.write_text("payload", encoding="utf-8")
    original = tmp_path / "original.txt"
    digest = "239f59ed55e737c77147cf55ad0c1b030b6d7ee748a7426952f9b852d5a935e5"
    rollback_file = tmp_path / "rollback.json"
    rollback_file.write_text(
        json.dumps(
            {
                "entries": [
                    {
                        "original_path": str(original),
                        "backup_path": str(backup),
                        "sha256": digest,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    exit_code = cli.main(["rollback", str(rollback_file), "--dry-run"])
    assert exit_code == 0
