"""System and sensitive file filtering logic."""
from __future__ import annotations

from pathlib import Path
from typing import Iterable, Iterator

from .models import FileCandidate

_DEFAULT_EXCLUDES = {
    ".DS_Store",
    "Thumbs.db",
    "__MACOSX",
    "__pycache__",
}

_SENSITIVE_KEYWORDS = {
    "password",
    "密碼",
    "private",
    "機密",
}


class SystemFilter:
    """Filter out files that should not be processed further."""

    def __init__(self, *, whitelist: Iterable[str] | None = None) -> None:
        self.whitelist = {item.lower() for item in whitelist or []}

    def filter_candidates(self, candidates: Iterable[FileCandidate]) -> Iterator[FileCandidate]:
        """Yield candidates that pass system and sensitive checks."""

        for candidate in candidates:
            if self._is_whitelisted(candidate.path):
                yield candidate
                continue

            if self._is_system_file(candidate.path):
                continue

            if self._contains_sensitive_keyword(candidate.path):
                candidate.tags.add("sensitive")
                yield candidate
                continue

            yield candidate

    def _is_system_file(self, path: Path) -> bool:
        name = path.name
        if name in _DEFAULT_EXCLUDES:
            return True
        if name.startswith("~$"):
            return True
        if path.suffix.lower() in {".tmp", ".temp"}:
            return True
        return False

    def _contains_sensitive_keyword(self, path: Path) -> bool:
        name_lower = path.name.lower()
        return any(keyword in name_lower for keyword in _SENSITIVE_KEYWORDS)

    def _is_whitelisted(self, path: Path) -> bool:
        if not self.whitelist:
            return False
        normalized = str(path).lower()
        return any(token in normalized for token in self.whitelist)
