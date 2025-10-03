from __future__ import annotations

from pathlib import Path

from auto_organizer.classifier import CategoryRule, ClassificationEngine
from auto_organizer.config import DuplicateStrategy, FileInfo, OrganizeOptions, Statistics
from auto_organizer.filters import SystemFileFilter
from auto_organizer.mover import FileMover
from auto_organizer.organizer import AutoOrganizer
from auto_organizer.report import ReportBuilder
from auto_organizer.scanner import FileScanner


def create_file(path: Path, content: str = "content") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def build_file_info(path: Path) -> FileInfo:
    return FileInfo(
        file_path=path,
        file_name=path.name,
        file_extension=path.suffix.lower(),
        file_size=path.stat().st_size if path.exists() else 0,
        creation_date=None,
        modification_date=None,
        source_folder=path.parent,
    )


def test_system_filter_rules_and_whitelist() -> None:
    filter_ = SystemFileFilter(["重要"])
    assert filter_.should_skip(".DS_Store", 10) is True
    assert filter_.should_skip("document.txt", 10) is False
    assert filter_.is_whitelisted("重要文件.txt") is True


def test_file_scanner_collects_metadata(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    normal_file = source / "report.txt"
    create_file(normal_file)
    system_file = source / ".DS_Store"
    create_file(system_file)

    options = OrganizeOptions(recursive=True)
    filter_ = SystemFileFilter(options.whitelist_patterns)
    scanner = FileScanner(options, filter_)

    results = scanner.scan(source)

    normal_entry = next(info for info in results if info.file_path == normal_file)
    system_entry = next(info for info in results if info.file_path == system_file)

    assert normal_entry.is_system_file is False
    assert system_entry.is_system_file is True
    assert system_entry.process_status == "skipped"


def test_classification_engine_scores_rules() -> None:
    engine = ClassificationEngine()
    documents_rule = CategoryRule(
        id="documents",
        name="📄 文件",
        emoji="📄",
        extensions=(".txt",),
        keywords=("report",),
        priority=10,
    )
    engine.rules[documents_rule.id] = documents_rule

    file_info = FileInfo(
        file_path=Path("dummy"),
        file_name="annual_report.txt",
        file_extension=".txt",
        file_size=1024,
        creation_date=None,
        modification_date=None,
        source_folder=Path("."),
    )

    category, score = engine.classify(file_info)

    assert category == documents_rule.name
    assert score >= documents_rule.priority


def test_classification_keywords_are_case_insensitive() -> None:
    engine = ClassificationEngine()
    keyword_rule = CategoryRule(
        id="notes",
        name="📝 筆記",
        emoji="📝",
        keywords=("notes",),
        priority=15,
    )
    engine.rules[keyword_rule.id] = keyword_rule

    file_info = FileInfo(
        file_path=Path("dummy"),
        file_name="Project_NOTES.txt",
        file_extension=".txt",
        file_size=512,
        creation_date=None,
        modification_date=None,
        source_folder=Path("."),
    )

    category, score = engine.classify(file_info)

    assert category == keyword_rule.name
    assert score >= keyword_rule.priority


def test_file_mover_duplicate_handling(tmp_path: Path) -> None:
    destination = tmp_path / "dest"
    destination.mkdir()
    original = destination / "data.txt"
    create_file(original, "old")

    mover = FileMover(DuplicateStrategy.RENAME)
    duplicate_file = tmp_path / "incoming.txt"
    create_file(duplicate_file, "new")
    info = build_file_info(duplicate_file)
    info.file_name = "data.txt"
    target = mover.move(info, destination)
    assert target is not None
    assert target.name != "data.txt"
    assert target.exists()

    mover_skip = FileMover(DuplicateStrategy.SKIP)
    another = tmp_path / "another.txt"
    create_file(another)
    info_skip = build_file_info(another)
    info_skip.file_name = "data.txt"
    assert mover_skip.move(info_skip, destination) is None


def test_report_builder_outputs_summary() -> None:
    builder = ReportBuilder()
    stats = Statistics(total_files=3, processed_files=2, skipped_items=1, duplicates=1)
    report = builder.build(stats, {"Documents": []})
    assert "AutoOrganizer Report" in report
    assert "Documents" in report
    assert "Processed files: 2" in report


def test_auto_organizer_end_to_end(tmp_path: Path) -> None:
    source = tmp_path / "source"
    target = tmp_path / "target"
    source.mkdir()
    target.mkdir()

    picture = source / "screenshot_photo.png"
    text_file = source / "project_document.txt"
    create_file(picture)
    create_file(text_file)

    options = OrganizeOptions()
    organizer = AutoOrganizer(options)

    result = organizer.organize([source], target)

    assert result.success is True
    assert result.processed_files == 2
    assert (target / "🖼️ 圖片" / picture.name).exists()
    assert (target / "📄 文件" / text_file.name).exists()
    report_path = target / "AutoOrganizer_report.txt"
    assert report_path.exists()

    report_content = report_path.read_text(encoding="utf-8")
    assert "Processed files" in report_content
