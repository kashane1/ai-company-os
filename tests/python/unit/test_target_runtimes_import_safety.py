"""Phase 0.5d.2 — target_runtimes must be a stdlib-only leaf module.

The Phase 5 command_scan policy imports this module transitively at
tool-wire-up time in packages/tools/codex_tools/cli.py and
packages/tools/worktrees.py. If target_runtimes pulled in the skill
loader or any module that parses registry.yaml, a Phase 0 regression
would take down worktree creation at import time.

This test uses importlib introspection to walk the module's transitive
closure and verifies every import is in the Python stdlib plus this
module's own `typing` usage.
"""
from __future__ import annotations

import importlib
import importlib.util
import sys


ALLOWED_NON_STDLIB = set()  # empty — target_runtimes must be pure stdlib


def _module_is_stdlib(name: str) -> bool:
    """True if the module is part of the Python standard library."""
    # Python 3.10+: sys.stdlib_module_names is the authoritative set.
    if hasattr(sys, "stdlib_module_names"):
        root = name.split(".")[0]
        return root in sys.stdlib_module_names
    # Fallback for older Pythons: check if the module lives under
    # Python's stdlib path.
    try:
        spec = importlib.util.find_spec(name)
    except (ImportError, ValueError):
        return False
    if spec is None or spec.origin is None:
        return False
    return "site-packages" not in spec.origin


def test_target_runtimes_import_has_no_side_effects() -> None:
    """Importing target_runtimes must not trigger any registry / YAML load."""
    # Clear any cached import so we observe the fresh import path.
    for cached in list(sys.modules):
        if cached.endswith("target_runtimes"):
            del sys.modules[cached]

    # Track which modules get imported as a side effect.
    before = set(sys.modules)
    import packages.tools.skills.target_runtimes as target_runtimes  # noqa: F401
    after = set(sys.modules)

    newly_imported = after - before

    # Remove the module itself and any of its parent packages from
    # the diff — those are expected.
    newly_imported.discard("packages.tools.skills.target_runtimes")

    # Any remaining new imports must be stdlib.
    non_stdlib = {
        name
        for name in newly_imported
        if not _module_is_stdlib(name) and name not in ALLOWED_NON_STDLIB
        # Filter out bare package containers (e.g. "packages",
        # "packages.tools") — these are empty __init__.py files that
        # Python auto-imports when resolving a dotted name. They don't
        # execute any side-effectful code.
        and not (
            name.startswith("packages")
            and _is_empty_package_init(name)
        )
    }

    assert not non_stdlib, (
        f"target_runtimes.py pulled in non-stdlib imports: {non_stdlib}. "
        "It MUST be a leaf module (stdlib-only) so a registry regression "
        "cannot take down worktree creation at tool-wire-up time."
    )


def _is_empty_package_init(module_name: str) -> bool:
    """True if `module_name` is a package __init__.py with no executable code."""
    mod = sys.modules.get(module_name)
    if mod is None:
        return False
    file = getattr(mod, "__file__", None)
    if file is None or not file.endswith("__init__.py"):
        return False
    try:
        with open(file, encoding="utf-8") as f:
            content = f.read()
    except OSError:
        return False
    # Strip docstrings + comments; any remaining non-empty line is
    # executable code.
    in_docstring = False
    docstring_quote = None
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if in_docstring:
            if docstring_quote in stripped:
                in_docstring = False
            continue
        if stripped.startswith(('"""', "'''")):
            quote = stripped[:3]
            if stripped.count(quote) >= 2:
                continue
            in_docstring = True
            docstring_quote = quote
            continue
        if stripped.startswith("#"):
            continue
        return False
    return True


def test_target_runtimes_constants_are_exported() -> None:
    from packages.tools.skills.target_runtimes import (
        TARGET_RUNTIMES,
        TargetRuntimeSlug,
    )
    assert TARGET_RUNTIMES == ("claude", "codex", "acp")
    # TargetRuntimeSlug is a Literal; can't instantiate, just verify
    # it exists as an attribute of the module.
    assert TargetRuntimeSlug is not None
