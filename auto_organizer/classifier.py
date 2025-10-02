"""File classification rules and engine."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Tuple

from .config import FileInfo


@dataclass
class CategoryRule:
    id: str
    name: str
    emoji: str
    extensions: Tuple[str, ...] = ()
    keywords: Tuple[str, ...] = ()
    mime_types: Tuple[str, ...] = ()
    min_size: int | None = None
    priority: int = 0


class ClassificationEngine:
    """Multi-layer rule-based file classifier."""

    DEFAULT_RULES: Tuple[CategoryRule, ...] = (
        CategoryRule(
            id="documents",
            name="📄 文件",
            emoji="📄",
            extensions=(".doc", ".docx", ".txt", ".rtf", ".pages", ".md"),
            keywords=("文件", "document", "報告", "report"),
            mime_types=("application/msword", "text/plain"),
            priority=10,
        ),
        CategoryRule(
            id="images",
            name="🖼️ 圖片",
            emoji="🖼️",
            extensions=(".jpg", ".jpeg", ".png", ".gif", ".heic", ".svg"),
            keywords=("screenshot", "截圖", "photo", "照片"),
            mime_types=("image/jpeg", "image/png", "image/gif"),
            priority=10,
        ),
        CategoryRule(
            id="code",
            name="💻 程式碼",
            emoji="💻",
            extensions=(".html", ".css", ".js", ".py", ".java", ".cpp", ".swift"),
            keywords=("source", "src", "code"),
            mime_types=("text/html", "application/javascript"),
            priority=10,
        ),
        CategoryRule(
            id="archives",
            name="📁 壓縮檔",
            emoji="📁",
            extensions=(".zip", ".rar", ".7z", ".tar", ".gz", ".dmg"),
            keywords=("backup", "備份", "archive", "download", "下載"),
            min_size=104_857_600,
            priority=8,
        ),
        CategoryRule(
            id="audio",
            name="🎵 音樂",
            emoji="🎵",
            extensions=(".mp3", ".m4a", ".wav", ".flac"),
            priority=10,
        ),
        CategoryRule(
            id="video",
            name="🎬 影片",
            emoji="🎬",
            extensions=(".mp4", ".mov", ".avi", ".mkv"),
            priority=10,
        ),
        CategoryRule(
            id="design",
            name="🎨 設計",
            emoji="🎨",
            extensions=(".psd", ".ai", ".sketch", ".figma"),
            priority=10,
        ),
        CategoryRule(
            id="spreadsheets",
            name="📊 試算表",
            emoji="📊",
            extensions=(".xlsx", ".xls", ".csv", ".numbers"),
            priority=10,
        ),
        CategoryRule(
            id="ebooks",
            name="📚 電子書",
            emoji="📚",
            extensions=(".epub", ".mobi", ".azw"),
            keywords=("book", "書", "manual", "手冊"),
            priority=10,
        ),
        CategoryRule(
            id="data",
            name="🗄️ 數據",
            emoji="🗄️",
            extensions=(".json", ".xml", ".sql"),
            priority=10,
        ),
        CategoryRule(
            id="apps",
            name="📦 應用程式",
            emoji="📦",
            extensions=(".pkg", ".app", ".exe"),
            priority=10,
        ),
    )

    DEFAULT_CATEGORY = CategoryRule(
        id="others", name="🗂️ 其他", emoji="🗂️", priority=0
    )

    def __init__(self) -> None:
        self.rules: Dict[str, CategoryRule] = {rule.id: rule for rule in self.DEFAULT_RULES}

    def classify(self, file_info: FileInfo) -> tuple[str, float]:
        scores: Dict[str, int] = {}

        for rule in self.rules.values():
            score = self._score_rule(rule, file_info)
            if score:
                scores[rule.id] = scores.get(rule.id, 0) + score

        if not scores:
            return self.DEFAULT_CATEGORY.name, 0.0

        best_id = max(scores, key=scores.get)
        best_rule = self.rules[best_id]
        return best_rule.name, float(scores[best_id])

    def load_custom_rules(self, path: Path) -> None:
        data = json.loads(path.read_text(encoding="utf-8"))
        categories = data.get("classificationRules", {}).get("categories", [])
        for category in categories:
            rules = category.get("rules", {})
            rule = CategoryRule(
                id=category["id"],
                name=category.get("name", category["id"]),
                emoji=category.get("emoji", ""),
                extensions=tuple(ext.lower() for ext in rules.get("extensions", [])),
                keywords=tuple(rules.get("keywords", [])),
                mime_types=tuple(rules.get("mimeTypes", [])),
                min_size=rules.get("minSize"),
                priority=rules.get("priority", 0),
            )
            self.rules[rule.id] = rule

    @staticmethod
    def _score_rule(rule: CategoryRule, file_info: FileInfo) -> int:
        score = 0
        if rule.extensions and file_info.file_extension in rule.extensions:
            score += rule.priority
        if rule.keywords and any(keyword in file_info.file_name for keyword in rule.keywords):
            score += rule.priority + 5
        if rule.min_size and file_info.file_size >= rule.min_size:
            score += max(5, rule.priority // 2)
        return score
