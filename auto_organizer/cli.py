"""Command line interface for AutoOrganizer."""

from __future__ import annotations

import argparse
from pathlib import Path

from .organizer import AutoOrganizer, OrganizeOptions


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="AutoOrganizer CLI")
    parser.add_argument("sources", nargs="+", help="Source folders to organize")
    parser.add_argument("--target", required=True, help="Target folder for organized files")
    parser.add_argument("--no-recursive", action="store_true", help="Disable recursive scanning")
    parser.add_argument("--skip-duplicates", action="store_true", help="Skip duplicates instead of renaming")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite duplicates")
    parser.add_argument("--rules", type=str, help="Path to custom classification rules JSON")
    parser.add_argument("--no-report", action="store_true", help="Do not generate report")
    return parser.parse_args()


def build_options(args: argparse.Namespace) -> OrganizeOptions:
    from .config import DuplicateStrategy

    strategy = DuplicateStrategy.RENAME
    if args.skip_duplicates:
        strategy = DuplicateStrategy.SKIP
    elif args.overwrite:
        strategy = DuplicateStrategy.OVERWRITE

    return OrganizeOptions(
        recursive=not args.no_recursive,
        handle_duplicates=strategy != DuplicateStrategy.SKIP,
        duplicate_strategy=strategy,
        generate_report=not args.no_report,
    )


def main() -> None:
    args = parse_args()
    options = build_options(args)
    organizer = AutoOrganizer(options)
    if args.rules:
        organizer.load_custom_rules(Path(args.rules))
    result = organizer.organize([Path(src) for src in args.sources], Path(args.target))
    if result.success:
        print(f"Processed {result.processed_files} files, {result.duplicates} duplicates handled.")
    else:
        print("Organization completed with errors:")
        for error in result.errors:
            print(f" - {error}")


if __name__ == "__main__":
    main()
