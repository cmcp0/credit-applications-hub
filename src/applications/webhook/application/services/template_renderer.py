from __future__ import annotations

import re
from typing import Any

TOKEN_PATTERN = re.compile(r"\{\{\s*([a-zA-Z0-9_.-]+)\s*\}\}")


def render_payload_template(
    template: dict[str, object],
    context: dict[str, Any],
) -> dict[str, object]:
    rendered: dict[str, object] = {}
    for key, value in template.items():
        rendered[key] = _render_value(value, context)
    return rendered


def _render_value(value: Any, context: dict[str, Any]) -> Any:
    if isinstance(value, dict):
        return {k: _render_value(v, context) for k, v in value.items()}
    if isinstance(value, list):
        return [_render_value(item, context) for item in value]
    if isinstance(value, str):
        return TOKEN_PATTERN.sub(lambda match: _resolve_path(context, match.group(1)), value)
    return value


def _resolve_path(context: dict[str, Any], path: str) -> str:
    cursor: Any = context
    for segment in path.split("."):
        if not isinstance(cursor, dict) or segment not in cursor:
            return ""
        cursor = cursor[segment]
    if cursor is None:
        return ""
    return str(cursor)

