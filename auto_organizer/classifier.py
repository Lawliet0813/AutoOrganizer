"""Rule-based classification engine."""
from __future__ import annotations

from collections import OrderedDict
import json
import logging
import mimetypes
import re
from typing import Iterable, Mapping, NamedTuple

from .models import ClassificationResult, FileCandidate

LOGGER_NAME = "auto_organizer.classifier"


class _Decision(NamedTuple):
    weight: int
    source: str
    category: str
    rationale: str


_RULE_PRIORITY: Mapping[str, int] = {
    "extension": 100,
    "keyword": 80,
    "size": 50,
    "mime": 60,
    "magic": 70,
}


def _normalise_suffix(suffix: str) -> str:
    if not suffix:
        return suffix
    if not suffix.startswith("."):
        return f".{suffix.lower()}"
    return suffix.lower()


class ClassificationEngine:
    """Classifies files into categories using configurable rules."""

    def __init__(
        self,
        rules: Mapping[str, object] | None = None,
        *,
        logger: logging.Logger | None = None,
    ) -> None:
        self.rules = rules or {}
        classification_rules = self.rules.get("classification") if isinstance(self.rules, Mapping) else None
        if isinstance(classification_rules, Mapping):
            self._rules = classification_rules
        else:
            self._rules = self.rules  # type: ignore[assignment]
        self.default_category: str = self.rules.get("default_category", "uncategorized") if isinstance(self.rules, Mapping) else "uncategorized"
        self.logger = logger or logging.getLogger(LOGGER_NAME)
        self._extension_cache: OrderedDict[str, str] = OrderedDict()
        self._cache_limit = 1000

    def classify(self, candidate: FileCandidate) -> ClassificationResult:
        """Classify a file and return a :class:`ClassificationResult`."""

        decisions: list[_Decision] = []

        extension_decision = self._classify_by_extension(candidate)
        if extension_decision:
            decisions.append(extension_decision)

        keyword_decision = self._classify_by_keyword(candidate)
        if keyword_decision:
            decisions.append(keyword_decision)

        size_decision = self._classify_by_size(candidate)
        if size_decision:
            decisions.append(size_decision)

        mime_decision = self._classify_by_mime(candidate)
        if mime_decision:
            decisions.append(mime_decision)

        magic_decision = self._classify_by_magic(candidate)
        if magic_decision:
            decisions.append(magic_decision)

        if decisions:
            decisions.sort(key=lambda d: (-d.weight, self._source_priority(d.source)))
            best = decisions[0]
            return ClassificationResult(
                category=best.category,
                confidence=min(best.weight / 100.0, 1.0),
                rationale=f"{best.source}:{best.rationale}",
            )

        return ClassificationResult(
            category=self.default_category,
            confidence=0.0,
            rationale="no-match",
        )

    # ------------------------------------------------------------------
    # Individual classification helpers
    def _classify_by_extension(self, candidate: FileCandidate) -> _Decision | None:
        suffix = _normalise_suffix(candidate.path.suffix)
        if not suffix:
            return None

        cached = self._extension_cache_get(suffix)
        if cached:
            return _Decision(_RULE_PRIORITY["extension"], "extension", cached, suffix)

        extension_rules = self._rules.get("extension", {})
        if isinstance(extension_rules, Mapping):
            if suffix in extension_rules:
                category = str(extension_rules[suffix])
                self._remember_extension(suffix, category)
                return _Decision(_RULE_PRIORITY["extension"], "extension", category, suffix)

        return None

    def _classify_by_keyword(self, candidate: FileCandidate) -> _Decision | None:
        keyword_rules = self._rules.get("keyword")
        if not isinstance(keyword_rules, Mapping):
            return None
        name = candidate.path.name.lower()
        keywords = self._tokenise(name)
        for keyword in keywords:
            if keyword in keyword_rules:
                category = str(keyword_rules[keyword])
                return _Decision(_RULE_PRIORITY["keyword"], "keyword", category, keyword)
        for pattern, category in keyword_rules.items():
            if pattern in keywords:
                continue
            try:
                if re.search(pattern, name):
                    return _Decision(_RULE_PRIORITY["keyword"], "keyword", str(category), pattern)
            except re.error:
                self._log_debug("Invalid keyword pattern", pattern)
        return None

    def _classify_by_size(self, candidate: FileCandidate) -> _Decision | None:
        size_rules = self._rules.get("size")
        if not isinstance(size_rules, Iterable):
            return None
        for rule in size_rules:
            if not isinstance(rule, Mapping):
                continue
            min_size = int(rule.get("min", 0)) if rule.get("min") is not None else None
            max_size = int(rule.get("max")) if rule.get("max") is not None else None
            category = rule.get("category")
            if not category:
                continue
            if min_size is not None and candidate.size < min_size:
                continue
            if max_size is not None and candidate.size > max_size:
                continue
            return _Decision(_RULE_PRIORITY["size"], "size", str(category), json.dumps(rule, ensure_ascii=False))
        return None

    def _classify_by_mime(self, candidate: FileCandidate) -> _Decision | None:
        mime_rules = self._rules.get("mime")
        if not isinstance(mime_rules, Mapping):
            return None
        mime_type, _ = mimetypes.guess_type(str(candidate.path))
        if not mime_type:
            return None
        for pattern, category in mime_rules.items():
            pattern_str = str(pattern)
            if mime_type == pattern_str or mime_type.startswith(pattern_str.rstrip("*")):
                return _Decision(_RULE_PRIORITY["mime"], "mime", str(category), mime_type)
        return None

    def _classify_by_magic(self, candidate: FileCandidate) -> _Decision | None:
        magic_rules = self._rules.get("magic")
        if not isinstance(magic_rules, Mapping):
            return None
        try:
            with candidate.path.open("rb") as fh:
                header = fh.read(32)
        except OSError:
            self._log_debug("Unable to read file for magic", str(candidate.path))
            return None
        for pattern, category in magic_rules.items():
            needle = self._parse_magic_pattern(str(pattern))
            if needle and header.startswith(needle):
                return _Decision(_RULE_PRIORITY["magic"], "magic", str(category), pattern)
        return None

    # ------------------------------------------------------------------
    # Helpers
    def _parse_magic_pattern(self, pattern: str) -> bytes | None:
        if pattern.startswith("0x"):
            try:
                return bytes.fromhex(pattern[2:])
            except ValueError:
                self._log_debug("Invalid hex magic pattern", pattern)
                return None
        return pattern.encode("utf-8")

    def _extension_cache_get(self, suffix: str) -> str | None:
        if suffix in self._extension_cache:
            category = self._extension_cache.pop(suffix)
            self._extension_cache[suffix] = category
            return category
        return None

    def _remember_extension(self, suffix: str, category: str) -> None:
        self._extension_cache[suffix] = category
        if len(self._extension_cache) > self._cache_limit:
            self._extension_cache.popitem(last=False)

    def _tokenise(self, name: str) -> set[str]:
        tokens = set(filter(None, re.split(r"[^a-z0-9]+", name)))
        return tokens

    def _log_debug(self, message: str, detail: str) -> None:
        if self.logger and self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug("%s: %s", message, detail)

    def _source_priority(self, source: str) -> int:
        order = ["extension", "keyword", "magic", "mime", "size"]
        try:
            return order.index(source)
        except ValueError:
            return len(order)
