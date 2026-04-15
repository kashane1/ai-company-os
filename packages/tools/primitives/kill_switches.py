"""Agent-readable kill-switch primitives (Phase 3, X5).

Filesystem kill switches live under ``state/flags/<switch_name>``. The
presence of the file means the switch is engaged — workers and tools
that check a switch should refuse to act until a human removes the file.

Write is human-only. There is no tool in this module that *creates* a
flag — an agent cannot freeze itself, nor an adjacent lane, by mistake
or by compromise. To engage a switch, a human runs ``touch
state/flags/<name>`` (or the equivalent operator CLI). Read is the
full contract: agents and policies ask "is X frozen?" and react.

This module lives under :mod:`packages.tools.primitives` so it is:

1. Stateless at module level — no file I/O at import time, no caches.
2. Side-effect-free to import — AST-enforced by
   ``tests/python/unit/test_primitives_conventions.py``.
3. Typed at the boundary — returns frozen dataclass :class:`KillSwitch`,
   not a dict or a raw bool.
4. No orchestration — each public function is one operation.

Why a frozen dataclass instead of a plain ``bool``?

The return value is cheap to construct and lets callers do structural
assertions in tests (``assert switch.name == "skill_evolution_frozen"``)
and policy composition without re-deriving the path at every call site.
It also makes future additions (expected_by, reason file, hash of the
operator who touched it) backward-compatible without breaking callers.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from packages.config.settings import load_runtime_paths


# Canonical switch names used across the platform. New switches MUST be
# added here — the module-level set is the single source of truth for
# "which switches exist?" and the enum is cheap compared to a future
# typo like ``skill_evolution_freeze`` vs ``skill_evolution_frozen``.
#
# Callers pass the string name into :func:`get_switch` which validates
# against this set.
KNOWN_SWITCHES: frozenset[str] = frozenset(
    {
        "gtm_frozen",
        "skill_evolution_frozen",
    }
)


@dataclass(frozen=True)
class KillSwitch:
    """Immutable view of a single kill switch at a point in time.

    ``path`` is absolute. ``engaged`` is the only field callers usually
    inspect — the rest exist for audit and debugging.
    """

    name: str
    path: str
    engaged: bool


class UnknownKillSwitchError(ValueError):
    """Raised when a caller asks about a switch not in ``KNOWN_SWITCHES``.

    Prevents typos from silently returning ``engaged=False`` for a
    switch that doesn't exist — that failure mode is exactly the one
    kill switches are supposed to prevent.
    """


def list_switches() -> tuple[KillSwitch, ...]:
    """Snapshot every known switch and its current state.

    Returns a tuple (immutable) so the result is safe to cache by the
    caller. Sorted by name so test diffs are stable.
    """
    return tuple(
        _inspect(name, _switch_path(name)) for name in sorted(KNOWN_SWITCHES)
    )


def get_switch(name: str) -> KillSwitch:
    """Read the current state of a single known switch.

    Raises :class:`UnknownKillSwitchError` if ``name`` is not in
    :data:`KNOWN_SWITCHES`. Use :func:`list_switches` to enumerate.
    """
    if name not in KNOWN_SWITCHES:
        raise UnknownKillSwitchError(
            f"kill switch {name!r} not registered; known switches: "
            f"{sorted(KNOWN_SWITCHES)}"
        )
    return _inspect(name, _switch_path(name))


def _switch_path(name: str) -> Path:
    """Resolve the filesystem location for a switch name.

    Uses :func:`packages.config.settings.load_runtime_paths` so tests
    that override ``AI_COMPANY_OS_STATE_ROOT`` (or equivalent) see the
    test-scoped switch dir, not the live production dir.
    """
    paths = load_runtime_paths()
    return paths.repo_root / "state" / "flags" / name


def _inspect(name: str, path: Path) -> KillSwitch:
    """Build a :class:`KillSwitch` from a name + path.

    Factored out so :func:`list_switches` and :func:`get_switch` share
    exactly one branch of file-existence handling.
    """
    return KillSwitch(
        name=name,
        path=str(path),
        engaged=path.exists(),
    )
