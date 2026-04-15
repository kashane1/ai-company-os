"""Phase 0.5c — LOC budget guard on dispatch_router.py.

The dispatch_router is a thin call-site that resolves
`target_runtime → Provider` and invokes `execute(task)`. Routing
*policy* lives in `packages/policies/provider_resolution.py`. Any
PR that grows the router beyond 50 LOC must move logic into policies
or providers, not into the router itself.

Arbitrary number, arbitrary enforcement — but arbitrary enforced
beats squishy aspirational. If a genuine need to raise the budget
arises, bump it here and leave a comment explaining why.
"""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
DISPATCH_ROUTER = (
    REPO_ROOT / "apps" / "runtime-supervisor" / "supervisor" / "dispatch_router.py"
)

# Budget excludes docstrings, blank lines, and pure comment lines so
# the budget reflects actual executable LOC, not documentation density.
BUDGET = 50


def _executable_lines(source: str) -> list[str]:
    """Return non-blank, non-comment, non-docstring lines."""
    lines = source.splitlines()
    result: list[str] = []
    in_docstring = False
    docstring_quote: str | None = None
    for raw in lines:
        stripped = raw.strip()
        if not stripped:
            continue
        # Simple docstring skip — module, class, and function docstrings
        # that start/end with triple quotes on their own line.
        if in_docstring:
            if docstring_quote and docstring_quote in stripped:
                in_docstring = False
                docstring_quote = None
            continue
        if stripped.startswith(('"""', "'''")):
            quote = stripped[:3]
            if stripped.count(quote) >= 2:
                # Single-line docstring.
                continue
            in_docstring = True
            docstring_quote = quote
            continue
        if stripped.startswith("#"):
            continue
        result.append(raw)
    return result


def test_dispatch_router_under_loc_budget() -> None:
    assert DISPATCH_ROUTER.exists(), (
        f"dispatch_router.py not found at {DISPATCH_ROUTER}. "
        "Phase 0.5c renames or moves the file."
    )
    source = DISPATCH_ROUTER.read_text()
    executable = _executable_lines(source)
    actual = len(executable)
    assert actual <= BUDGET, (
        f"dispatch_router.py has {actual} executable LOC, "
        f"budget is {BUDGET}. Move logic into "
        f"packages/policies/provider_resolution.py or "
        f"packages/tools/providers/ before growing the router."
    )
