from __future__ import annotations

from auto_organizer.scheduler import build_schedule, launch_agent_payload, write_launch_agent


def test_scheduler_builds_plan(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    scan_dir = tmp_path / "scan"
    scan_dir.mkdir()
    (scan_dir / "file1.txt").write_text("data", encoding="utf-8")

    plan = build_schedule("quick", [scan_dir])
    assert plan.interval_minutes in {30, 60}
    assert plan.log_path.parent.exists()

    payload = launch_agent_payload(plan, "autoorganizer")
    destination = write_launch_agent(payload, tmp_path / "agent.plist")
    assert destination.exists()
