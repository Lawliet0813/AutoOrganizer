from __future__ import annotations

from datetime import datetime
from pathlib import Path

from auto_organizer.models import FileCandidate
from auto_organizer.system_filter import SystemFilter


def make_candidate(tmp_path: Path, name: str, size: int = 1) -> FileCandidate:
    path = tmp_path / name
    path.write_bytes(b"x" * size)
    return FileCandidate(path=path, size=size, modified_at=datetime.utcnow())


def test_hidden_file_is_skipped(tmp_path: Path) -> None:
    candidate = make_candidate(tmp_path, ".hidden", size=0)
    system_filter = SystemFilter()
    decision = system_filter.evaluate(candidate)
    assert decision.should_skip
    assert decision.reason == "hidden"
    assert "hidden" in decision.flags


def test_whitelisted_file_bypasses_rules(tmp_path: Path) -> None:
    candidate = make_candidate(tmp_path, ".hidden_doc")
    system_filter = SystemFilter(whitelist=[str(candidate.path)])
    decision = system_filter.evaluate(candidate)
    assert not decision.should_skip
    assert "whitelisted" in decision.flags


def test_sensitive_keyword_flags_and_skips(tmp_path: Path) -> None:
    candidate = make_candidate(tmp_path, "secret_password.txt")
    system_filter = SystemFilter()
    decision = system_filter.evaluate(candidate)
    assert decision.should_skip
    assert decision.reason == "sensitive_keyword"
    assert "sensitive" in decision.flags


def test_temporary_and_cloud_placeholder(tmp_path: Path) -> None:
    candidate = make_candidate(tmp_path, "tempfile.tmp")
    placeholder = make_candidate(tmp_path, "icloud.data.icloud", size=0)
    system_filter = SystemFilter()
    temp_decision = system_filter.evaluate(candidate)
    cloud_decision = system_filter.evaluate(placeholder)
    assert temp_decision.should_skip
    assert "temporary" in temp_decision.flags
    assert cloud_decision.should_skip
    assert cloud_decision.reason == "cloud_placeholder"
