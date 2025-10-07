from __future__ import annotations

import json
from pathlib import Path

import pytest

from auto_organizer.rules import CURRENT_RULES_VERSION, RulesValidationError, upgrade_rules, validate_rules


def _write_rules(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def test_validate_rules_success(tmp_path) -> None:
    rules_path = tmp_path / "rules.json"
    _write_rules(
        rules_path,
        {
            "version": CURRENT_RULES_VERSION,
            "rules": {
                "documents": {"extensions": [".pdf", ".docx"]}
            },
        },
    )

    data = validate_rules(rules_path)
    assert data["rules"]["documents"]["extensions"] == [".pdf", ".docx"]


def test_validate_rules_failure_reports_line(tmp_path) -> None:
    rules_path = tmp_path / "broken.json"
    rules_path.write_text("{""version"": ""1.0""}", encoding="utf-8")
    with pytest.raises(RulesValidationError) as exc:
        validate_rules(rules_path)
    assert exc.value.line == 1


def test_upgrade_rules(tmp_path) -> None:
    legacy_path = tmp_path / "legacy.json"
    _write_rules(
        legacy_path,
        {
            "version": "1.0",
            "categories": {
                "media": [".mp4"]
            },
        },
    )

    upgraded = upgrade_rules(legacy_path)
    assert upgraded["version"] == CURRENT_RULES_VERSION
    assert upgraded["rules"]["media"]["extensions"] == [".mp4"]

    # Ensure upgraded file validates
    validate_rules(legacy_path)
