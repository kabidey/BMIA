"""
JSON response utilities — sanitizes NaN/Inf to None (JSON-null) so that
pandas/numpy-derived floats never crash Starlette's json.dumps(allow_nan=False).
"""
import json
import math
from typing import Any

from fastapi.responses import JSONResponse


def _sanitize(obj: Any) -> Any:
    """Recursively replace NaN/Inf floats with None."""
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize(v) for v in obj]
    if isinstance(obj, tuple):
        return tuple(_sanitize(v) for v in obj)
    return obj


class SafeJSONResponse(JSONResponse):
    """Drop-in JSONResponse that tolerates NaN/Inf in nested content."""

    def render(self, content: Any) -> bytes:
        sanitized = _sanitize(content)
        return json.dumps(
            sanitized,
            ensure_ascii=False,
            allow_nan=False,
            indent=None,
            separators=(",", ":"),
        ).encode("utf-8")
