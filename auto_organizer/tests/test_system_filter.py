from pathlib import Path
from datetime import datetime
from auto_organizer.system_filter import SystemFilter
from auto_organizer.models import FileCandidate

def create_candidate(path_str: str) -> FileCandidate:
    """Helper to create a FileCandidate instance."""
    return FileCandidate(
        path=Path(path_str),
        size=1024,
        modified_at=datetime(2023, 1, 1, 12, 0, 0)
    )

def test_filter_system_files():
    """Test that default system files are filtered out."""
    sys_filter = SystemFilter()
    candidates = [
        create_candidate("/tmp/.DS_Store"),
        create_candidate("/tmp/Thumbs.db"),
        create_candidate("/tmp/__MACOSX"),
        create_candidate("/tmp/__pycache__"),
        create_candidate("/tmp/some_dir/~$tempfile.docx"),
        create_candidate("/tmp/another.tmp"),
        create_candidate("/tmp/archive.temp"),
    ]

    result = list(sys_filter.filter_candidates(candidates))
    assert len(result) == 0

def test_sensitive_keywords():
    """Test that files with sensitive keywords are tagged."""
    sys_filter = SystemFilter()
    candidates = [
        create_candidate("/secrets/password.txt"),
        create_candidate("/data/我的密碼.zip"),
        create_candidate("/keys/private_key.pem"),
        create_candidate("/docs/機密文件.docx"),
        create_candidate("/normal/document.txt"),
    ]

    result = list(sys_filter.filter_candidates(candidates))

    assert len(result) == 5

    # Check sensitive tags
    assert "sensitive" in result[0].tags
    assert "sensitive" in result[1].tags
    assert "sensitive" in result[2].tags
    assert "sensitive" in result[3].tags

    # Check normal file
    assert "sensitive" not in result[4].tags

def test_whitelisted_files():
    """Test that whitelisted files are not filtered."""
    # Whitelist a path that contains a system file name to test precedence
    sys_filter = SystemFilter(whitelist=["/safe/.DS_Store"])

    candidates = [
        create_candidate("/safe/.DS_Store"),  # Should be yielded due to whitelist
        create_candidate("/tmp/.DS_Store"),     # Should be filtered
    ]

    result = list(sys_filter.filter_candidates(candidates))

    assert len(result) == 1
    assert result[0].path == Path("/safe/.DS_Store")

def test_whitelisted_partial_path():
    """Test that partial path whitelisting works."""
    sys_filter = SystemFilter(whitelist=["/safe/"])

    candidates = [
        create_candidate("/safe/some_file.txt"),
        create_candidate("/safe/subfolder/.DS_Store"), # Whitelisted directory
        create_candidate("/unsafe/other_file.txt"),
    ]

    result = list(sys_filter.filter_candidates(candidates))

    assert len(result) == 3
    paths = {c.path for c in result}
    assert Path("/safe/some_file.txt") in paths
    assert Path("/safe/subfolder/.DS_Store") in paths
    assert Path("/unsafe/other_file.txt") in paths

def test_no_filters_match():
    """Test that normal files pass through correctly."""
    sys_filter = SystemFilter()
    candidates = [
        create_candidate("/documents/report.docx"),
        create_candidate("/images/photo.jpg"),
    ]

    result = list(sys_filter.filter_candidates(candidates))

    assert len(result) == 2
    paths = {c.path for c in result}
    assert Path("/documents/report.docx") in paths
    assert Path("/images/photo.jpg") in paths

def test_empty_input():
    """Test that the filter handles empty input."""
    sys_filter = SystemFilter()
    result = list(sys_filter.filter_candidates([]))
    assert len(result) == 0

def test_mixed_scenario():
    """Test a mix of system, sensitive, and normal files."""
    sys_filter = SystemFilter(whitelist=["/work/project_a"])
    candidates = [
        create_candidate("/home/user/~$document.docx"), # System
        create_candidate("/personal/my_password.txt"), # Sensitive
        create_candidate("/work/project_a/report.pdf"), # Whitelisted
        create_candidate("/downloads/image.png"),       # Normal
        create_candidate("/tmp/.DS_Store"),             # System
    ]

    result = list(sys_filter.filter_candidates(candidates))

    assert len(result) == 3

    paths = {c.path for c in result}
    assert Path("/personal/my_password.txt") in paths
    assert Path("/work/project_a/report.pdf") in paths
    assert Path("/downloads/image.png") in paths

    sensitive_file = next(c for c in result if c.path == Path("/personal/my_password.txt"))
    assert "sensitive" in sensitive_file.tags