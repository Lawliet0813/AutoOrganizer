from __future__ import annotations

from datetime import datetime
from pathlib import Path

from auto_organizer.classifier import ClassificationEngine
from auto_organizer.models import FileCandidate


def make_candidate(path: Path, size: int = 0) -> FileCandidate:
    return FileCandidate(path=path, size=size, modified_at=datetime.utcnow())


def test_extension_and_cache(tmp_path: Path) -> None:
    rules = {
        "classification": {
            "extension": {".pdf": "documents"},
        },
        "default_category": "misc",
    }
    engine = ClassificationEngine(rules)
    candidate = make_candidate(tmp_path / "report.pdf")
    result = engine.classify(candidate)
    assert result.category == "documents"
    assert result.confidence == 1.0
    # Second call should hit cache
    result_cached = engine.classify(make_candidate(tmp_path / "another.pdf"))
    assert result_cached.category == "documents"


def test_keyword_and_size_rules(tmp_path: Path) -> None:
    rules = {
        "classification": {
            "keyword": {"invoice": "finance"},
            "size": [
                {"max": 1024, "category": "small"},
            ],
        },
        "default_category": "misc",
    }
    engine = ClassificationEngine(rules)
    keyword_candidate = make_candidate(tmp_path / "invoice_2023.txt")
    result_keyword = engine.classify(keyword_candidate)
    assert result_keyword.category == "finance"
    small_candidate = make_candidate(tmp_path / "blob", size=512)
    result_size = engine.classify(small_candidate)
    assert result_size.category == "small"


def test_magic_and_mime_detection(tmp_path: Path) -> None:
    pdf_path = tmp_path / "sample.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\ncontent")
    rules = {
        "classification": {
            "extension": {},
            "magic": {"%PDF-": "documents"},
            "mime": {"text/plain": "text"},
        },
        "default_category": "misc",
    }
    engine = ClassificationEngine(rules)
    pdf_candidate = make_candidate(pdf_path, size=pdf_path.stat().st_size)
    result_pdf = engine.classify(pdf_candidate)
    assert result_pdf.category == "documents"
    text_path = tmp_path / "notes.txt"
    text_path.write_text("notes", encoding="utf-8")
    text_candidate = make_candidate(text_path, size=text_path.stat().st_size)
    result_text = engine.classify(text_candidate)
    assert result_text.category in {"text", "misc"}
