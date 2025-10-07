from __future__ import annotations

import json
from datetime import datetime, timedelta

from auto_organizer.reporter import ReportGenerator, RunSummary


def test_report_generator_roundtrip(tmp_path) -> None:
    started = datetime(2024, 1, 1, 12, 0, 0)
    finished = started + timedelta(minutes=5)
    summary = RunSummary(
        started_at=started,
        finished_at=finished,
        classification_counts={"documents": 3, "media": 1},
        moved_files=3,
        skipped_files=1,
        reclaimed_bytes=4096,
        errors=[{"path": "/tmp/file", "message": "permission denied"}],
    )

    generator = ReportGenerator()
    payload = generator.build_payload(summary)
    json_path, txt_path = generator.write(payload, tmp_path)

    saved = json.loads(json_path.read_text(encoding="utf-8"))
    assert saved["totals"]["processed"] == 4
    assert saved["classification"]["documents"] == 3
    assert "permission denied" in txt_path.read_text(encoding="utf-8")
