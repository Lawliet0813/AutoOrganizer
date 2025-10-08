from __future__ import annotations

from auto_organizer.file_mover import FileMover
from auto_organizer.logger import configure_logging, next_log_path
from auto_organizer.models import PlanItem


def make_plan_item(source, destination, operation="rename") -> PlanItem:
    return PlanItem(
        source=source,
        destination=destination,
        operation=operation,
        same_volume=True,
        size=source.stat().st_size,
        conflict=False,
    )


def test_file_mover_rename_and_copy(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    logger = configure_logging(next_log_path("move-test"))
    mover = FileMover(logger)

    src = tmp_path / "src.txt"
    src.write_text("data", encoding="utf-8")
    dst = tmp_path / "dest.txt"

    mover.execute(make_plan_item(src, dst, operation="rename"))
    assert dst.exists()

    # copy scenario
    src2 = tmp_path / "src2.txt"
    src2.write_text("more", encoding="utf-8")
    dst2 = tmp_path / "dest2.txt"
    item = PlanItem(
        source=src2,
        destination=dst2,
        operation="copy",
        same_volume=False,
        size=src2.stat().st_size,
        conflict=False,
    )
    mover.execute(item)
    assert dst2.exists()


def test_cross_volume_move_deletes_source(tmp_path, monkeypatch) -> None:
    """Verify that a cross-volume move (copy) deletes the source file."""
    monkeypatch.setenv("HOME", str(tmp_path))
    logger = configure_logging(next_log_path("cross-volume-test"))
    mover = FileMover(logger)

    # 1. Setup
    source_dir = tmp_path / "source_vol"
    dest_dir = tmp_path / "dest_vol"
    source_dir.mkdir()
    dest_dir.mkdir()

    source_file = source_dir / "test_file.txt"
    source_file.write_text("cross-volume data")
    destination_file = dest_dir / "test_file.txt"

    # 2. Create a plan item for a cross-volume move
    plan_item = PlanItem(
        source=source_file,
        destination=destination_file,
        operation="copy",  # Cross-volume moves are treated as 'copy'
        same_volume=False,
        size=source_file.stat().st_size,
        conflict=False,
    )

    # 3. Execute the move
    mover.execute(plan_item)

    # 4. Verify
    assert destination_file.exists()
    assert destination_file.read_text() == "cross-volume data"
    assert not source_file.exists(), "Source file should be deleted after a successful cross-volume move"
