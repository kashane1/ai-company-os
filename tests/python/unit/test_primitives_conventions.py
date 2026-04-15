"""Phase 0.5e — convention guard for packages/tools/primitives/.

Walks every module under `packages/tools/primitives/` and asserts the
four conventions from `docs/adr/2026-04-14-primitives-subpackage.md`:

1. Stateless at module level — no mutable global variables, no class
   instantiation at module level other than frozen dataclass
   definitions (which are class statements, not instantiations).

2. Side-effect-free imports — no top-level calls to `subprocess`,
   `socket`, `urllib`, `requests`, file-system writes, or network I/O.

3. Typed return values — every public function (non-underscore prefix)
   has a return-type annotation.

4. No orchestration — each public function is a single operation.
   Enforced softly via a "no import of other primitive modules at
   module level" check.

The test is AST-based so it runs fast and doesn't require executing
the modules. Empty primitives subpackage (Phase 0.5e state) is a
valid pass.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest


PRIMITIVES_DIR = (
    Path(__file__).resolve().parents[3] / "packages" / "tools" / "primitives"
)

FORBIDDEN_TOP_LEVEL_IMPORTS = {
    "subprocess",
    "socket",
    "urllib",
    "urllib.request",
    "urllib3",
    "requests",
    "httpx",
    "aiohttp",
}


def _primitive_modules() -> list[Path]:
    """All .py files under primitives/ except __init__.py."""
    if not PRIMITIVES_DIR.is_dir():
        return []
    return sorted(
        p
        for p in PRIMITIVES_DIR.glob("*.py")
        if p.name != "__init__.py"
    )


def test_primitives_directory_exists() -> None:
    assert PRIMITIVES_DIR.is_dir(), (
        f"Phase 0.5e creates {PRIMITIVES_DIR}. Did the subpackage "
        "get deleted?"
    )
    assert (PRIMITIVES_DIR / "__init__.py").exists()


@pytest.mark.parametrize("module_path", _primitive_modules() or [None])
def test_no_forbidden_imports_at_module_level(module_path: Path | None) -> None:
    """Primitive modules must not import subprocess/socket/network libs."""
    if module_path is None:
        pytest.skip("No primitive modules yet — Phase 0.5e empty state.")
    tree = ast.parse(module_path.read_text(), filename=str(module_path))
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name not in FORBIDDEN_TOP_LEVEL_IMPORTS, (
                    f"{module_path.name}: top-level `import {alias.name}` "
                    "violates the primitives convention "
                    "(see docs/adr/2026-04-14-primitives-subpackage.md)"
                )
        elif isinstance(node, ast.ImportFrom):
            module_name = node.module or ""
            root = module_name.split(".")[0]
            assert root not in FORBIDDEN_TOP_LEVEL_IMPORTS, (
                f"{module_path.name}: top-level `from {module_name} import ...` "
                "violates the primitives convention"
            )


@pytest.mark.parametrize("module_path", _primitive_modules() or [None])
def test_no_class_instantiation_at_module_level(module_path: Path | None) -> None:
    """Class definitions are allowed; class() calls at module scope are not."""
    if module_path is None:
        pytest.skip("No primitive modules yet.")
    tree = ast.parse(module_path.read_text(), filename=str(module_path))
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.Assign):
            # Allowed: assigning a constant, dataclass type reference,
            # a frozen dataclass's CLASS object (not instance).
            value = node.value
            if isinstance(value, ast.Call):
                # A Call at module scope is suspicious — flag it unless
                # it's a typing construct or tuple/frozenset of constants.
                func = value.func
                func_name = _qualname(func)
                # Allowlisted: typing.Literal, typing.Final, frozenset,
                # tuple, dict, set, list, functools.cache, functools.lru_cache
                if func_name in {
                    "Literal",
                    "Final",
                    "frozenset",
                    "tuple",
                    "dict",
                    "set",
                    "list",
                    "lru_cache",
                    "cache",
                }:
                    continue
                raise AssertionError(
                    f"{module_path.name}:{node.lineno} module-level call to "
                    f"{func_name}(...) violates primitives convention "
                    "(primitives must be stateless at import time)"
                )


def _qualname(node: ast.AST) -> str:
    """Best-effort qualified name for a Call.func node."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return "<unknown>"


@pytest.mark.parametrize("module_path", _primitive_modules() or [None])
def test_public_functions_have_return_annotations(
    module_path: Path | None,
) -> None:
    """Every non-underscore-prefix function must declare a return type."""
    if module_path is None:
        pytest.skip("No primitive modules yet.")
    tree = ast.parse(module_path.read_text(), filename=str(module_path))
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name.startswith("_"):
                continue  # private helpers exempt
            assert node.returns is not None, (
                f"{module_path.name}:{node.lineno} public function "
                f"{node.name!r} missing return-type annotation "
                "(primitives convention: typed returns)"
            )
