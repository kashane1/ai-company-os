"""Atomic state writer primitive (ECC Gap Recommendations Phase 2a).

Per todo 007 + todo 011, every JSON write under `state/health/**` and
`state/artifacts/verification-loop/**` routes through this helper.
It guarantees:

1. Atomic replace via temp file + `os.replace` (no partial writes).
2. Parent directory bootstrap (`mkdir(parents=True, exist_ok=True)`)
   so first-run writes never fail on missing directories.
3. Stable `run_id` format for per-run artifact subdirs.
4. Collision protection: writing to an existing run-id directory
   raises `RunIdCollision` rather than silently overwriting.
5. `schema_version` key on every report (injected at write time if
   absent) so readers can gate on version.

Per the primitives convention:
- Stateless module-level.
- No forbidden top-level imports.
- Typed returns.
"""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "1"


class RunIdCollision(RuntimeError):
    """Raised when atomic_write_json targets an existing run-id dir."""


def new_run_id() -> str:
    """Return a new stable run-id.

    Format: `<ISO8601-UTC>Z-<uuid4[:8]>`. Sortable, unique, and
    human-readable — e.g. `2026-04-15T14-30-00Z-a1b2c3d4`. Colons in
    the ISO timestamp are replaced with dashes so the string is a
    valid filesystem segment on every platform.
    """
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    suffix = uuid.uuid4().hex[:8]
    return f"{ts}-{suffix}"


def atomic_write_json(
    path: Path,
    report: dict[str, Any],
    *,
    allow_overwrite: bool = False,
) -> None:
    """Write `report` to `path` atomically.

    Ensures parent directory exists (mkdir parents=True, exist_ok=True).
    Injects `schema_version: "1"` at the top of the report if absent
    — every on-disk state artifact MUST carry a schema version.

    Raises `RunIdCollision` when `path` already exists and
    `allow_overwrite` is False. The default prevents two concurrent
    writers from trampling each other under the same run-id.

    The write itself is atomic: we dump to `<path>.tmp-<uuid>` in the
    same directory, then `os.replace` to the final path. Both the temp
    and target sit on the same filesystem so the rename is atomic.
    """
    if not isinstance(report, dict):
        raise TypeError(
            f"report must be a dict; got {type(report).__name__}"
        )
    if path.exists() and not allow_overwrite:
        raise RunIdCollision(
            f"atomic_write_json refused to overwrite {path!s}; "
            "pass allow_overwrite=True only if you know this is safe"
        )
    path.parent.mkdir(parents=True, exist_ok=True)

    # Inject schema_version if absent. Preserves existing value on
    # re-writes (allow_overwrite=True) so downstream readers don't see
    # version drift for no reason.
    if "schema_version" not in report:
        report = {"schema_version": SCHEMA_VERSION, **report}

    tmp_path = path.with_name(f"{path.name}.tmp-{uuid.uuid4().hex[:8]}")
    try:
        with tmp_path.open("w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, sort_keys=True)
            f.write("\n")
        os.replace(tmp_path, path)
    except Exception:
        # Best-effort cleanup on failure — we never want a dangling
        # `.tmp-<uuid>` orphan.
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)
        raise
