"""Agent-callable follow-up writer (ECC Gap Recommendations todo 005).

The plan repeatedly says drift surfaced by `skill-stocktake` is
"captured as a follow-up issue". Before this primitive existed,
"captured" meant "an operator manually files a GitHub issue", which
is an agent-native parity gap. `skill-stocktake`, `verification-loop`,
and any other agent-callable drift detector now route through this
writer to emit a typed YAML file under `state/followups/`.

The emitted file is a structured `FollowupEntry`:

    ---
    id: <slug>
    source: <skill-id or module>
    severity: info | warn | fail | error
    title: <short imperative>
    body: <multiline detail>
    affected_files: [<paths>]
    captured_at: <ISO8601 UTC>
    ---

Written atomically via `_state_writer.atomic_write_json` using a
YAML-like `.yaml` suffix because downstream readers (`verification-loop`
aggregator, operator-facing listing tool) expect YAML.

Convention per the primitives ADR:
- Stateless module.
- Side-effect-free import.
- Typed returns.
- No top-level I/O.
"""
from __future__ import annotations

import re
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

import yaml

Severity = Literal["info", "warn", "fail", "error"]


@dataclass(frozen=True)
class FollowupEntry:
    """One follow-up captured by an agent for deferred resolution."""

    id: str
    source: str
    severity: Severity
    title: str
    body: str
    affected_files: tuple[str, ...] = ()
    captured_at: str = ""


def _slugify(text: str) -> str:
    """Lowercase, non-alnum → dash, collapse dashes, strip edges."""
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:48] or "followup"


def _repo_root() -> Path:
    """Repo root derived from this module's filesystem location.

    Kept private so primitives don't leak filesystem assumptions.
    """
    return Path(__file__).resolve().parents[3]


def _followups_dir() -> Path:
    return _repo_root() / "state" / "followups"


def write(entry: FollowupEntry) -> Path:
    """Write `entry` to `state/followups/<yyyy-mm-dd>-<slug>.yaml`.

    Bootstraps the directory on first write
    (`mkdir(parents=True, exist_ok=True)`). Collisions are avoided by
    appending a short uuid suffix when two entries share a slug on
    the same day.

    Returns the absolute path the entry was written to.
    """
    captured = entry.captured_at or datetime.now(timezone.utc).isoformat()
    entry_dict = asdict(entry)
    entry_dict["captured_at"] = captured

    day = captured[:10]
    slug = _slugify(entry.title)
    root = _followups_dir()
    root.mkdir(parents=True, exist_ok=True)

    path = root / f"{day}-{slug}.yaml"
    if path.exists():
        path = root / f"{day}-{slug}-{uuid.uuid4().hex[:6]}.yaml"

    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(entry_dict, f, sort_keys=True, default_flow_style=False)
    return path


def make_entry(
    *,
    source: str,
    severity: Severity,
    title: str,
    body: str,
    affected_files: tuple[str, ...] = (),
) -> FollowupEntry:
    """Factory helper — builds a `FollowupEntry` with a derived id.

    The id is `<source>-<slug>-<uuid8>` so duplicate captures from
    multiple runs are distinguishable.
    """
    return FollowupEntry(
        id=f"{source}-{_slugify(title)}-{uuid.uuid4().hex[:8]}",
        source=source,
        severity=severity,
        title=title,
        body=body,
        affected_files=affected_files,
    )
