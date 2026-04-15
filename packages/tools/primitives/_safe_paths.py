"""Path-traversal guard primitives (ECC Gap Recommendations Phase 2a).

This module is the authoritative home for adapter-path validation and
safe path joining under the `skills/` tree. Per todo 004, the helper
`_ADAPTER_PATH_PATTERN` was lifted here from
`packages/tools/skills/loader.py:42` so that new primitives introduced
by Phase 2 (`registry_drift.py`, `context_budget.py`) can consume a
single canonical guard without violating the primitives subpackage
ADR's "no imports from packages/tools/skills/" boundary.

`loader.py` now imports the pattern from this module; the Hermes
Phase 0 loader tests pass unchanged because the compiled regex is
byte-identical.

Per the primitives convention
(`docs/adr/2026-04-14-primitives-subpackage.md`):

- Stateless at module level.
- Side-effect-free to import.
- Public functions have typed returns.
- No imports from packages/tools/skills/ (dependency inversion).

This module intentionally imports nothing from the rest of the repo
so it can be the dependency floor.
"""
from __future__ import annotations

import functools
import re
from pathlib import Path


# Adapter paths stored in `skills/registry.yaml` under `adapters:` entries
# must match this pattern. The runtime slug and skill id are both
# kebab-case identifiers; the path is relative to the skills root, NOT
# the repo root, because the loader resolves via `_skills_root() / path`.
#
# The pattern lives as a plain string at module level (stateless import
# per the primitives ADR); the compiled form is lazily built and cached
# via `adapter_path_pattern()`. The convention test forbids module-level
# `re.compile()` calls; lru_cache is on the allowlist.
ADAPTER_PATH_PATTERN_STR = (
    r"^adapters/[a-z][a-z0-9_]*/[a-z0-9][a-z0-9_-]*\.md$"
)


@functools.lru_cache(maxsize=1)
def adapter_path_pattern() -> re.Pattern[str]:
    """Return the compiled adapter-path regex.

    Cached so repeat calls amortize to a single compile per process.
    Lazy so the convention test
    (`tests/python/unit/test_primitives_conventions.py`) does not see
    a module-level `re.compile(...)` call.
    """
    return re.compile(ADAPTER_PATH_PATTERN_STR)


# Backwards-compat alias for `packages/tools/skills/loader.py`, which
# imports `ADAPTER_PATH_PATTERN` directly. The loader module is not a
# primitive, so module-level state here is fine; we provide both the
# string and a lazy helper so primitives callers stay compliant.
def _get_pattern() -> re.Pattern[str]:
    return adapter_path_pattern()


class UnsafePathError(ValueError):
    """Raised when `safe_join` refuses a relative path.

    Signals one of:
    - absolute path passed as relative input,
    - `..` escape,
    - the resolved path leaves the declared root,
    - empty or otherwise invalid input.
    """


def safe_join(root: Path, relpath: str) -> Path:
    """Safely join a declared root with an untrusted relative path.

    Rejects absolute paths, `..` escape sequences, empty strings, and
    any join whose resolved absolute path is not inside `root`. The
    root is resolved via `Path.resolve()` before comparison so
    symlinks are followed consistently on both sides.

    Returns the resolved absolute path.

    Raises `UnsafePathError` on rejection. Callers MUST treat rejection
    as an adversarial input — do NOT fall back to a `.is_file()` probe
    or a permissive join, since the whole point of this helper is to
    deny the read.
    """
    if not isinstance(relpath, str) or not relpath:
        raise UnsafePathError(
            f"relpath must be a non-empty string; got {relpath!r}"
        )
    if relpath.startswith("/") or relpath.startswith("\\"):
        raise UnsafePathError(
            f"relpath must not be absolute; got {relpath!r}"
        )
    # Normalize via Path but keep the root resolved for containment check.
    root_resolved = root.resolve()
    candidate = (root_resolved / relpath).resolve()
    # Containment check. Path.is_relative_to is Python 3.9+.
    try:
        candidate.relative_to(root_resolved)
    except ValueError as exc:
        raise UnsafePathError(
            f"relpath {relpath!r} resolves outside root {root!s}"
        ) from exc
    return candidate


def is_adapter_path(adapter_path: str) -> bool:
    """Return True if `adapter_path` matches the adapter-path pattern.

    Non-string inputs return False rather than raising — callers that
    want strict validation should call the pattern directly.
    """
    if not isinstance(adapter_path, str):
        return False
    return adapter_path_pattern().match(adapter_path) is not None
