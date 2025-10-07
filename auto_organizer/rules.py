"""Rule management utilities for AutoOrganizer."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence


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


# -- helpers ------------------------------------------------------------
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
    "load_rules",
    "upgrade_rules",
    "validate_rules",
]
