"""System file filtering logic."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Tuple


@dataclass
class FilterRule:
    pattern: str
    rule_type: str
    action: str
    reason: str
    threshold: int | None = None


class SystemFileFilter:
    """Determine whether a file should be skipped based on rules."""

    DEFAULT_RULES: Tuple[FilterRule, ...] = (
        FilterRule("OneDrive", "contains", "skip", "OneDrive 同步檔案"),
        FilterRule("iCloud", "contains", "skip", "iCloud 同步檔案"),
        FilterRule("Dropbox", "contains", "skip", "Dropbox 同步檔案"),
        FilterRule("Google Drive", "contains", "skip", "Google Drive 檔案"),
        FilterRule(".", "startsWith", "skip", "隱藏檔案"),
        FilterRule(".DS_Store", "equals", "skip", "macOS 系統檔案"),
        FilterRule("Thumbs.db", "equals", "skip", "Windows 快取檔案"),
        FilterRule(".git", "contains", "skip", "Git 版本控制"),
        FilterRule("node_modules", "contains", "skip", "Node.js 依賴"),
        FilterRule("__pycache__", "contains", "skip", "Python 快取"),
        FilterRule(".vscode", "contains", "skip", "VSCode 設定"),
        FilterRule("", "length", "skip", "檔名過長", threshold=100),
        FilterRule("~$", "startsWith", "skip", "暫存檔案"),
    )

    def __init__(self, whitelist_patterns: Iterable[str]) -> None:
        self.rules: List[FilterRule] = list(self.DEFAULT_RULES)
        self.whitelist_patterns = tuple(whitelist_patterns)

    def should_skip(self, file_name: str, file_size: int) -> bool:
        """Return True if file should be skipped as a system file."""

        for rule in self.rules:
            if self._matches(rule, file_name):
                return True
        return file_size < 1

    def is_whitelisted(self, file_name: str) -> bool:
        """Return True if filename matches whitelist patterns."""

        return any(pattern in file_name for pattern in self.whitelist_patterns)

    def add_rule(self, rule: FilterRule) -> None:
        self.rules.append(rule)

    @staticmethod
    def _matches(rule: FilterRule, file_name: str) -> bool:
        if rule.rule_type == "contains":
            return rule.pattern in file_name
        if rule.rule_type == "startsWith":
            return file_name.startswith(rule.pattern)
        if rule.rule_type == "equals":
            return file_name == rule.pattern
        if rule.rule_type == "length" and rule.threshold is not None:
            return len(file_name) > rule.threshold
        return False

