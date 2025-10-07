"""Rule-based classification engine skeleton."""
from __future__ import annotations

from collections import OrderedDict
from pathlib import Path
from typing import Mapping

from .models import ClassificationResult, FileCandidate

# Priority mapping inspired by the specification.
_RULE_PRIORITY = OrderedDict(
    {
        "extension": 100,
        "keyword": 80,
        "mime": 60,
        "magic": 70,
        "size": 50,
    }
)


class ClassificationEngine:
    """Classifies files into categories using configurable rules."""

    def __init__(self, rules: Mapping[str, Mapping[str, str]] | None = None) -> None:
        self.rules = rules or {}
        self._extension_cache: OrderedDict[str, str] = OrderedDict()
        self._cache_limit = 1000

    def classify(self, candidate: FileCandidate) -> ClassificationResult:
        """Classify a file and return a :class:`ClassificationResult`."""

        category = self._classify_by_extension(candidate.path)
        if category is None:
            category = "uncategorized"

        rationale = f"extension:{candidate.path.suffix or 'none'}"
        confidence = 0.0
        if category != "uncategorized":
            confidence = _RULE_PRIORITY["extension"] / 100

        return ClassificationResult(category=category, confidence=confidence, rationale=rationale)

    def _classify_by_extension(self, path: Path) -> str | None:
        suffix = path.suffix.lower()
        if not suffix:
            return None

        if suffix in self._extension_cache:
            category = self._extension_cache.pop(suffix)
            self._extension_cache[suffix] = category
            return category

        category = None
        extension_rules = self.rules.get("extension", {})
        if suffix in extension_rules:
            category = extension_rules[suffix]

        if category:
            self._remember_extension(suffix, category)
        return category

    def _remember_extension(self, suffix: str, category: str) -> None:
        self._extension_cache[suffix] = category
        if len(self._extension_cache) > self._cache_limit:
            self._extension_cache.popitem(last=False)
