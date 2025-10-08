"""Rule management utilities for AutoOrganizer."""
from __future__ import annotations

import json
import logging
import re
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional, Sequence

from .utils.fs import ensure_directory, unique_path


CURRENT_RULES_VERSION = "2.0"
DEFAULT_SCHEMA_PATH = Path(__file__).with_name("rules.schema.json")


@dataclass(slots=True)
class RulesValidationError(Exception):
    """Raised when a rules file does not comply with the schema."""

    message: str
    path: tuple[str | int, ...] | None = None
    line: int | None = None
    column: int | None = None

    def __str__(self) -> str:  # pragma: no cover - dataclass repr is enough for tests
        location = ""
        if self.line is not None:
            location = f" (line {self.line}, column {self.column or 1})"
        pointer = ""
        if self.path:
            pointer = " at $" + ".".join(str(part) for part in self.path)
        return f"{self.message}{pointer}{location}"


@dataclass(slots=True)
class PlannedMove:
    """Representation of a single file move operation."""

    src: Path
    dst: Path
    category: str
    reason: str


@dataclass(slots=True)
class MovePlan:
    """Aggregate information describing a planned classification run."""

    items: list[PlannedMove]
    scanned: int
    movable: int
    created_dirs: set[Path]


def load_rules(path: str | Path) -> Mapping[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def validate_rules(path: str | Path, schema_path: str | Path | None = None) -> Mapping[str, Any]:
    schema = json.loads(Path(schema_path or DEFAULT_SCHEMA_PATH).read_text(encoding="utf-8"))
    file_path = Path(path)
    content = file_path.read_text(encoding="utf-8")
    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise RulesValidationError(exc.msg, path=None, line=exc.lineno, column=exc.colno) from exc

    _validate_against_schema(data, schema, content)

    version = data.get("version")
    if version != CURRENT_RULES_VERSION:
        raise RulesValidationError(
            f"Unsupported rules version: {version!r}; expected {CURRENT_RULES_VERSION}",
            path=("version",),
            line=_locate_pointer(content, ("version",))[0],
            column=_locate_pointer(content, ("version",))[1],
        )
    return data


def upgrade_rules(
    path: str | Path,
    *,
    output: str | Path | None = None,
) -> Mapping[str, Any]:
    input_path = Path(path)
    content = json.loads(input_path.read_text(encoding="utf-8"))
    upgraded = _apply_migrations(content)
    destination = Path(output) if output else input_path
    destination.write_text(json.dumps(upgraded, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return upgraded


def preview(
    config: Path,
    sources: list[Path],
    target: Path,
    limit: Optional[int],
    output: Optional[Path],
) -> int:
    """Simulate file moves based on classification *config*."""

    logger = logging.getLogger("auto_organizer")
    plan = _build_plan(config, sources, target, limit, logger)
    _emit_preview(plan, output, logger)
    return 0


def apply(
    config: Path,
    sources: list[Path],
    target: Path,
    limit: Optional[int],
    output: Optional[Path],
    rollback: Optional[Path],
    dry_run: bool,
) -> int:
    """Apply classification rules, optionally moving files."""

    logger = logging.getLogger("auto_organizer")
    plan = _build_plan(config, sources, target, limit, logger)
    if dry_run:
        logger.info("Running in dry-run mode; no files will be moved")
        _emit_preview(plan, output, logger)
        return 0

    if not plan.items:
        logger.info("No files to move.")
        _emit_preview(plan, output, logger)
        return 0

    rollback_path = rollback or target / "rollback.json"
    ensure_directory(rollback_path.parent)
    ensure_directory(target)

    moved: list[PlannedMove] = []
    errors: list[str] = []
    for item in plan.items:
        try:
            ensure_directory(item.dst.parent)
            shutil.move(str(item.src), str(item.dst))
            moved.append(item)
            logger.info("Moved %s -> %s", item.src, item.dst)
        except Exception as exc:  # pragma: no cover - safety net
            logger.error("Failed to move %s: %s", item.src, exc)
            errors.append(str(item.src))

    _emit_preview(plan, output, logger)

    if moved:
        _write_rollback(rollback_path, moved)
        logger.info("Rollback information written to %s", rollback_path)

    if errors:
        logger.error("Encountered %d errors during apply", len(errors))
        return 1
    return 0


# -- helpers ------------------------------------------------------------

def _build_plan(
    config: Path,
    sources: Iterable[Path],
    target: Path,
    limit: Optional[int],
    logger: logging.Logger,
) -> MovePlan:
    ruleset = _load_classification_rules(config)
    planned: list[PlannedMove] = []
    created_dirs: set[Path] = set()
    reserved: set[Path] = set()

    scanned = 0
    for file_path in _iter_source_files(sources):
        if limit is not None and scanned >= limit:
            break
        scanned += 1

        category, reason = _classify(file_path, ruleset)
        destination_dir = target / category
        created_dirs.add(destination_dir)
        candidate = unique_path(destination_dir / file_path.name, reserved=reserved)
        planned.append(PlannedMove(src=file_path, dst=candidate, category=category, reason=reason))

    logger.info(
        "Planned %d move(s) out of %d scanned file(s) using config %s",
        len(planned),
        scanned,
        config,
    )

    return MovePlan(items=planned, scanned=scanned, movable=len(planned), created_dirs=created_dirs)


def _emit_preview(plan: MovePlan, output: Optional[Path], logger: logging.Logger) -> None:
    if plan.items:
        header = f"{'Source':<50} {'Category':<15} Destination"
        print(header)
        print("-" * len(header))
        for item in plan.items:
            print(f"{str(item.src):<50} {item.category:<15} {item.dst}")
    else:
        print("No files to process.")

    dirs = sorted({str(path) for path in plan.created_dirs})
    print()
    print(f"Scanned files: {plan.scanned}")
    print(f"Movable files: {plan.movable}")
    if dirs:
        print("Directories to create:")
        for directory in dirs:
            print(f"  - {directory}")

    if output:
        ensure_directory(output.parent)
        if output.suffix.lower() == ".json":
            payload = {
                "items": [
                    {
                        "src": str(item.src),
                        "category": item.category,
                        "dst": str(item.dst),
                        "reason": item.reason,
                    }
                    for item in plan.items
                ],
                "stats": {"scanned": plan.scanned, "movable": plan.movable},
                "created_dirs": dirs,
            }
            output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            logger.info("Preview written to %s", output)
        elif output.suffix.lower() == ".md":
            lines = [
                "# Rules Preview",
                "",
                "| Source | Category | Destination | Reason |",
                "| --- | --- | --- | --- |",
            ]
            for item in plan.items:
                lines.append(
                    f"| {item.src} | {item.category} | {item.dst} | {item.reason} |"
                )
            lines.extend(
                [
                    "",
                    "## Summary",
                    f"- Scanned files: {plan.scanned}",
                    f"- Movable files: {plan.movable}",
                ]
            )
            if dirs:
                lines.append("- Directories to create:")
                lines.extend(f"  - {directory}" for directory in dirs)
            output.write_text("\n".join(lines) + "\n", encoding="utf-8")
            logger.info("Preview written to %s", output)
        else:
            raise ValueError(f"Unsupported output format: {output.suffix}")


def _write_rollback(path: Path, moved: Iterable[PlannedMove]) -> None:
    payload = {
        "version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "items": [
            {
                "src": str(item.src),
                "dst": str(item.dst),
            }
            for item in moved
        ],
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _load_classification_rules(path: Path) -> Mapping[str, Any]:
    data = load_rules(path)
    rules = data.get("classificationRules")
    if not isinstance(rules, Mapping):
        raise RulesValidationError("Missing 'classificationRules' section", path=("classificationRules",))
    categories = rules.get("categories")
    if not isinstance(categories, list):
        raise RulesValidationError("'categories' must be a list", path=("classificationRules", "categories"))
    default = rules.get("defaultCategory")
    if not isinstance(default, Mapping) or "id" not in default:
        raise RulesValidationError(
            "Missing default category id",
            path=("classificationRules", "defaultCategory"),
        )
    return {
        "categories": categories,
        "default": str(default["id"]),
    }


def _iter_source_files(sources: Iterable[Path]) -> Iterable[Path]:
    for source in sources:
        if not source.exists():
            continue
        if source.is_file():
            yield source
            continue
        for entry in source.rglob("*"):
            if entry.is_file():
                yield entry


def _classify(path: Path, ruleset: Mapping[str, Any]) -> tuple[str, str]:
    extension = path.suffix.lower()
    size = path.stat().st_size
    for raw in ruleset["categories"]:
        if not isinstance(raw, Mapping):
            continue
        category_id = str(raw.get("id", ""))
        rule = raw.get("rules", {})
        if not category_id:
            continue
        extensions = {ext.lower() for ext in rule.get("extensions", []) if isinstance(ext, str)}
        min_size = rule.get("minSize")
        if extensions and extension not in extensions:
            continue
        if min_size is not None and size < int(min_size):
            continue
        reason = f"matched extension {extension}" if extensions else "matched rule"
        if min_size is not None:
            reason += f" and size >= {int(min_size)}"
        return category_id, reason
    return str(ruleset["default"]), "no matching rule"


def _apply_migrations(data: Mapping[str, Any]) -> Mapping[str, Any]:
    version = str(data.get("version", "1.0"))
    rules = dict(data)
    if version == CURRENT_RULES_VERSION:
        return rules

    if version == "1.0":
        categories = rules.pop("categories", None)
        if categories is not None and "rules" not in rules:
            rules["rules"] = categories
        transformed: dict[str, Any] = {}
        for name, value in rules.get("rules", {}).items():
            if isinstance(value, list):
                transformed[name] = {"extensions": value}
            elif isinstance(value, Mapping):
                transformed[name] = dict(value)
        rules["rules"] = transformed
        rules["version"] = CURRENT_RULES_VERSION
        return rules

    raise RulesValidationError(f"Cannot upgrade from version {version}")


def _validate_against_schema(data: Any, schema: Mapping[str, Any], content: str, path: Sequence[str | int] = ()) -> None:
    schema_type = schema.get("type")
    if schema_type:
        _validate_type(data, schema_type, content, path)

    if schema_type == "object":
        _validate_object(data, schema, content, path)
    elif schema_type == "array":
        _validate_array(data, schema, content, path)

    if "enum" in schema and data not in schema["enum"]:
        raise _error("Value not allowed", content, path)


def _validate_type(data: Any, schema_type: str | Sequence[str], content: str, path: Sequence[str | int]) -> None:
    types = (schema_type,) if isinstance(schema_type, str) else tuple(schema_type)
    python_types = {
        "object": dict,
        "array": list,
        "string": str,
        "integer": int,
        "number": (int, float),
        "boolean": bool,
    }
    if not any(isinstance(data, python_types[t]) for t in types if t in python_types):
        allowed = ", ".join(types)
        raise _error(f"Expected type {allowed}", content, path)


def _validate_object(data: Mapping[str, Any], schema: Mapping[str, Any], content: str, path: Sequence[str | int]) -> None:
    if not isinstance(data, Mapping):
        raise _error("Expected object", content, path)

    min_props = schema.get("minProperties")
    if min_props is not None and len(data) < int(min_props):
        raise _error(f"Expected at least {min_props} properties", content, path)

    required = schema.get("required", [])
    for key in required:
        if key not in data:
            raise _error(f"Missing required property '{key}'", content, path + (key,))

    properties: Mapping[str, Any] = schema.get("properties", {})
    pattern_props: Mapping[str, Any] = schema.get("patternProperties", {})
    additional = schema.get("additionalProperties", True)

    for key, value in data.items():
        if key in properties:
            _validate_against_schema(value, properties[key], content, path + (key,))
            continue

        matched = False
        for pattern, pattern_schema in pattern_props.items():
            if re.fullmatch(pattern, key):
                matched = True
                _validate_against_schema(value, pattern_schema, content, path + (key,))
                break
        if matched:
            continue

        if isinstance(additional, Mapping):
            _validate_against_schema(value, additional, content, path + (key,))
        elif additional is False:
            raise _error(f"Unexpected property '{key}'", content, path + (key,))


def _validate_array(data: Sequence[Any], schema: Mapping[str, Any], content: str, path: Sequence[str | int]) -> None:
    if not isinstance(data, Sequence) or isinstance(data, (str, bytes)):
        raise _error("Expected array", content, path)

    item_schema = schema.get("items")
    if item_schema:
        for index, item in enumerate(data):
            _validate_against_schema(item, item_schema, content, path + (index,))

    min_items = schema.get("minItems")
    if min_items is not None and len(data) < int(min_items):
        raise _error(f"Expected at least {min_items} items", content, path)


def _error(message: str, content: str, path: Sequence[str | int]) -> RulesValidationError:
    line, column = _locate_pointer(content, path)
    if line is None:
        line, column = 1, 1
    return RulesValidationError(message, tuple(path) if path else None, line, column)


def _locate_pointer(content: str, path: Sequence[str | int]) -> tuple[int | None, int | None]:
    if not path:
        return None, None
    key = path[-1]
    if isinstance(key, str):
        needle = f'"{key}"'
        for idx, line in enumerate(content.splitlines(), start=1):
            column = line.find(needle)
            if column != -1:
                return idx, column + 1
    return None, None


__all__ = [
    "CURRENT_RULES_VERSION",
    "RulesValidationError",
    "apply",
    "load_rules",
    "preview",
    "upgrade_rules",
    "validate_rules",
]
