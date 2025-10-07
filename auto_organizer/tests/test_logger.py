from __future__ import annotations

import json
import logging
from pathlib import Path

from auto_organizer.logger import configure_logging, log_event


def test_log_event_sanitizes_home_directory(tmp_path: Path) -> None:
    log_file = tmp_path / "auto.log"
    logger = configure_logging(log_file, level=logging.INFO)
    sensitive_path = Path.home() / "Documents" / "secret.txt"
    log_event(
        logger,
        level=logging.INFO,
        action="test",
        message="Processing",
        extra={"path": str(sensitive_path)},
    )
    for handler in logger.handlers:
        handler.flush()
    contents = log_file.read_text(encoding="utf-8").strip().splitlines()
    assert contents
    payload = json.loads(contents[-1])
    assert payload["path"].startswith("~/")
