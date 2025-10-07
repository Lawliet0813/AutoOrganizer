"""System and sensitive file filtering logic following the specification."""
from __future__ import annotations

from pathlib import Path
from typing import Iterable, Iterator

from .models import FileCandidate, FilterDecision

_DEFAULT_EXCLUDES = {
    ".DS_Store",
    "Thumbs.db",
    "__MACOSX",
    "__pycache__",
    ".git",
    ".svn",
    "node_modules",
}

_TEMP_SUFFIXES = {".tmp", ".temp", ".part", ".partial"}
_TEMP_PREFIXES = {"~$", "._"}

_CLOUD_PLACEHOLDER_SUFFIXES = {".icloud", ".icloud~", ".onepkg", ".one"}
_CLOUD_PLACEHOLDER_KEYWORDS = {"onedrive", "dropbox", "icloud"}

_SENSITIVE_KEYWORDS = {
    "password",
    "密碼",
    "private",
    "機密",
    "confidential",
    "secret",
}

_DEVELOPER_FOLDERS = {"build", "dist", "venv", ".venv", "env", ".idea"}


class SystemFilter:
    """Filter out files that should not be processed further."""

    def __init__(
        self,
        *,
        whitelist: Iterable[str] | None = None,
        sensitive_keywords: Iterable[str] | None = None,
        max_name_length: int = 255,
        skip_hidden: bool = True,
        skip_empty: bool = True,
        sensitive_action: str = "skip",
    ) -> None:
        self.whitelist = {item.lower() for item in whitelist or []}
        self.sensitive_keywords = {
            *(keyword.lower() for keyword in sensitive_keywords or []),
            *_SENSITIVE_KEYWORDS,
        }
        self.max_name_length = max_name_length
        self.skip_hidden = skip_hidden
        self.skip_empty = skip_empty
        if sensitive_action not in {"skip", "flag"}:
            raise ValueError("sensitive_action must be 'skip' or 'flag'")
        self.sensitive_action = sensitive_action

    def evaluate(self, candidate: FileCandidate) -> FilterDecision:
        """Evaluate a candidate and return a :class:`FilterDecision`."""

        flags: set[str] = set()
        should_skip = False
        reason: str | None = None
        path = candidate.path

        if self._is_whitelisted(path):
            flags.add("whitelisted")
            return FilterDecision(candidate, False, None, flags)

        checks: list[tuple[bool, str, str]] = [
            (self._is_cloud_placeholder(path, candidate.size), "cloud_placeholder", "cloud-placeholder"),
            (self.skip_hidden and self._is_hidden(path), "hidden", "hidden"),
            (self._is_system_file(path), "system", "system"),
            (self._is_developer_path(path), "developer", "developer"),
            (self._is_temporary(path), "temporary", "temporary"),
            (self._is_name_too_long(path), "name_too_long", "long-name"),
            (self.skip_empty and candidate.size == 0, "empty_file", "empty"),
        ]

        for condition, reason_token, flag in checks:
            if condition:
                flags.add(flag)
                if reason is None:
                    reason = reason_token
                should_skip = True

        sensitive_flag = self._contains_sensitive_keyword(path)
        if sensitive_flag:
            flags.add("sensitive")
            if self.sensitive_action == "skip":
                should_skip = True
                if reason is None:
                    reason = "sensitive_keyword"

        return FilterDecision(candidate, should_skip, reason, flags)

    def filter_candidates(self, candidates: Iterable[FileCandidate]) -> Iterator[FileCandidate]:
        """Yield candidates that pass system and sensitive checks."""

        for candidate in candidates:
            decision = self.evaluate(candidate)
            if not decision.should_skip:
                yield decision.candidate

    def iter_decisions(self, candidates: Iterable[FileCandidate]) -> Iterator[FilterDecision]:
        """Yield :class:`FilterDecision` for each candidate."""

        for candidate in candidates:
            yield self.evaluate(candidate)

    def _is_system_file(self, path: Path) -> bool:
        name = path.name
        if name in _DEFAULT_EXCLUDES:
            return True
        if any(part in _DEFAULT_EXCLUDES for part in path.parts):
            return True
        return False

    def _is_hidden(self, path: Path) -> bool:
        return any(part.startswith(".") and part not in {"..", "."} for part in path.parts)

    def _is_temporary(self, path: Path) -> bool:
        name = path.name
        if any(name.startswith(prefix) for prefix in _TEMP_PREFIXES):
            return True
        if any(name.endswith(suffix) for suffix in _TEMP_SUFFIXES):
            return True
        if name.endswith("~"):
            return True
        return False

    def _is_developer_path(self, path: Path) -> bool:
        return any(part.lower() in _DEVELOPER_FOLDERS for part in path.parts)

    def _is_name_too_long(self, path: Path) -> bool:
        return len(path.name.encode("utf-8")) > self.max_name_length

    def _contains_sensitive_keyword(self, path: Path) -> bool:
        name_lower = path.name.lower()
        return any(keyword in name_lower for keyword in self.sensitive_keywords)

    def _is_cloud_placeholder(self, path: Path, size: int) -> bool:
        name_lower = path.name.lower()
        if any(name_lower.endswith(suffix) for suffix in _CLOUD_PLACEHOLDER_SUFFIXES):
            return True
        if size == 0 and any(keyword in str(path).lower() for keyword in _CLOUD_PLACEHOLDER_KEYWORDS):
            return True
        return False

    def _is_whitelisted(self, path: Path) -> bool:
        if not self.whitelist:
            return False
        normalized = str(path).lower()
        return any(token in normalized for token in self.whitelist)
