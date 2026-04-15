"""Target-runtime slug constants — leaf module with zero side imports.

This module MUST remain a stdlib-only leaf (no imports from
packages.tools.skills.loader or any other module that touches the
filesystem / registry / YAML). Phase 5's command_scan policy imports
this module transitively at tool-wire-up time, so side-effectful
imports here would make a Phase 0 regression take down worktree
creation.

The content is just a Literal type + tuple constant. Anything that
wants to know which runtime slugs are valid imports from here;
the loader imports FROM here, never the reverse.

Validated by tests/python/unit/test_target_runtimes_import_safety.py.
"""
from __future__ import annotations

from typing import Final, Literal

# Canonical target-runtime slugs the platform understands. Adding a
# new slug (e.g. "hermes" for Phase 2 spike results) is a single-line
# edit in this file plus matching provider wiring in
# packages/tools/providers/.
TargetRuntimeSlug = Literal["claude", "codex", "acp"]

TARGET_RUNTIMES: Final[tuple[str, ...]] = ("claude", "codex", "acp")
