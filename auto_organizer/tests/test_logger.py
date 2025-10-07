from __future__ import annotations

import logging

from auto_organizer.logger import configure_logging, next_log_path


def test_logger_creates_rotated_files(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    logging.getLogger("auto_organizer").handlers.clear()
    log_path = next_log_path("rotation-test")
    log_path.write_bytes(b"0" * (5 * 1024 * 1024 + 10))

    logger = configure_logging(log_path, level=logging.DEBUG)
    logger.debug("rotation check")

    rotated = log_path.with_suffix(log_path.suffix + ".1")
    assert rotated.exists()
