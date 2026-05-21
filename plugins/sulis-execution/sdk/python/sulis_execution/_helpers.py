"""Internal helpers for resource modules.

Avoids per-resource duplication of envelope-unwrapping logic.
"""
from __future__ import annotations

from typing import Any


def _kwargs_to_params(kwargs: dict[str, Any]) -> dict[str, Any]:
    """Drop None values and pass through the rest.

    The transport handles snake_case → kebab-case argv conversion;
    this helper just filters out unset optional args.
    """
    return {k: v for k, v in kwargs.items() if v is not None}


def _result_payload(envelope: dict[str, Any]) -> dict[str, Any]:
    """Pull the result/data payload out of the wpx envelope.

    The wpx tools have two emit patterns:
    1. emit_ok(data={...}) → {"ok": true, "data": {...}}
    2. emit_result(record) → {"ok": true, "data": {"result": {...}}}
       (used by wpx-pipeline run and wpx-train run)

    Both return the inner payload (the dict that the Pydantic model
    should validate against).
    """
    data = envelope.get("data") or {}
    if "result" in data and isinstance(data["result"], dict):
        return data["result"]
    return data
