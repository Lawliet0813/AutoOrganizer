from __future__ import annotations

from datetime import datetime, timezone
from auto_organizer.classifier import ClassificationEngine
from auto_organizer.models import FileCandidate


def test_classifier_uses_extension_cache(tmp_path) -> None:
    engine = ClassificationEngine({"extension": {".txt": "docs"}})
    file_path = tmp_path / "note.txt"
    file_path.write_text("hello", encoding="utf-8")
    candidate = FileCandidate(
        path=file_path,
        size=5,
        modified_at=datetime.now(timezone.utc),
        is_symlink=False,
    )

    result1 = engine.classify(candidate)
    assert result1.category == "docs"

    # Populate cache and request again
    result2 = engine.classify(candidate)
    assert result2.category == "docs"
