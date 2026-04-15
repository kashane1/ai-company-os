"""JSON-safe serialization helpers (ECC Gap Recommendations Phase 2a).

Per todo 006, every validator whose return path uses
`dataclasses.asdict()` needs a dict factory that coerces
non-JSON-native types at construction time. Otherwise the first real
run crashes on `json.dumps()` when a `Path`, `Enum`, or `datetime`
lands in a dataclass field.

Usage:

    from dataclasses import asdict
    from packages.tools.primitives._serialization import json_safe_factory

    return asdict(report, dict_factory=json_safe_factory)

The factory also sorts keys so the output is deterministic — stable
output is a contract for the redaction / diff pipelines downstream.
"""
from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import Any, Iterable


def _coerce(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    # Recursively coerce list / tuple / set contents so nested
    # dataclass-derived structures also serialize cleanly.
    if isinstance(value, (list, tuple)):
        return [_coerce(v) for v in value]
    if isinstance(value, set):
        return sorted(_coerce(v) for v in value)
    if isinstance(value, dict):
        return {str(k): _coerce(v) for k, v in sorted(value.items())}
    return value


def json_safe_factory(pairs: Iterable[tuple[str, Any]]) -> dict[str, Any]:
    """dict_factory for `dataclasses.asdict(...)` that coerces types.

    Coerces `Path → str`, `Enum → .value`, `datetime/date → .isoformat()`.
    Keys are sorted so the output is stable across runs.
    """
    return {key: _coerce(value) for key, value in sorted(pairs)}
