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
